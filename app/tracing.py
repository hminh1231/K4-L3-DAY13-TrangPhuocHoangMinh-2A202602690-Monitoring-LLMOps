from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Any

try:
    from dotenv import load_dotenv

    # Langfuse reads credentials at import time. Load .env before that import.
    load_dotenv()
except ImportError:  # pragma: no cover - chỉ dùng khi chưa cài requirements
    pass

os.environ.setdefault(
    "OTEL_SERVICE_NAME",
    os.getenv("APP_NAME", "day13-monitoring-llmops-lab"),
)
# Default SDK timeout is 5s. On a slow connect, urllib3 spends that budget
# connecting and then fails the read with timeout 0.
os.environ.setdefault("LANGFUSE_TIMEOUT", "20")

try:
    from langfuse import get_client, observe, propagate_attributes

    LANGFUSE_SDK_AVAILABLE = True
except ImportError:  # pragma: no cover - chỉ dùng khi chưa cài requirements
    LANGFUSE_SDK_AVAILABLE = False

    def observe(*args: Any, **kwargs: Any):
        def decorator(func):
            return func

        return decorator

    class _DummyClient:
        def update_current_span(self, **kwargs: Any) -> None:
            return None

        def update_current_generation(self, **kwargs: Any) -> None:
            return None

        def score_current_trace(self, **kwargs: Any) -> None:
            return None

        def flush(self) -> None:
            return None

    def get_client():
        return _DummyClient()

    @contextmanager
    def propagate_attributes(**kwargs: Any):
        yield


def get_langfuse_client():
    return get_client()


def tracing_enabled() -> bool:
    return LANGFUSE_SDK_AVAILABLE and bool(
        os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY")
    )
