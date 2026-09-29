from __future__ import annotations

import random
import time
from dataclasses import dataclass
from datetime import datetime, timezone

from .incidents import STATE
from .pii import scrub_text
from .tracing import get_langfuse_client, observe

# Same rates as LabAgent._estimate_cost so the generation cost matches request metrics.
_INPUT_USD_PER_MILLION = 3
_OUTPUT_USD_PER_MILLION = 15


@dataclass
class FakeUsage:
    input_tokens: int
    output_tokens: int


@dataclass
class FakeResponse:
    text: str
    usage: FakeUsage
    model: str
    ttft_ms: int


class FakeLLM:
    def __init__(self, model: str = "claude-sonnet-4-5") -> None:
        self.model = model

    @observe(name="generate-response", as_type="generation", capture_input=False, capture_output=False)
    def generate(self, prompt: str) -> FakeResponse:
        started = time.perf_counter()
        time.sleep(0.05)  # mô phỏng thời điểm token đầu tiên sẵn sàng
        ttft_ms = int((time.perf_counter() - started) * 1000)
        completion_start_time = datetime.now(timezone.utc)
        time.sleep(0.10)
        input_tokens = max(20, len(prompt) // 4)
        output_tokens = random.randint(80, 180)
        if STATE["cost_spike"]:
            output_tokens *= 4
        answer = (
            "Starter answer. You should improve this output logic and add better quality checks. "
            "Use retrieved context and keep responses concise."
        )
        get_langfuse_client().update_current_generation(
            model=self.model,
            input=[{"role": "user", "content": scrub_text(prompt)}],
            output=[{"role": "assistant", "content": scrub_text(answer)}],
            completion_start_time=completion_start_time,
            usage_details={"input": input_tokens, "output": output_tokens},
            cost_details={
                "input": round((input_tokens / 1_000_000) * _INPUT_USD_PER_MILLION, 6),
                "output": round((output_tokens / 1_000_000) * _OUTPUT_USD_PER_MILLION, 6),
            },
            metadata={"ttft_ms": ttft_ms},
        )
        return FakeResponse(
            text=answer,
            usage=FakeUsage(input_tokens, output_tokens),
            model=self.model,
            ttft_ms=ttft_ms,
        )
