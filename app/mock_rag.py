from __future__ import annotations

import time

from .incidents import STATE
from .pii import scrub_text
from .tracing import get_langfuse_client, observe

CORPUS = {
    "refund": ["Refunds are available within 7 days with proof of purchase."],
    "monitoring": ["Metrics detect incidents, logs identify affected requests, traces localize the root cause."],
    "policy": ["Do not expose PII in logs. Use sanitized summaries only."],
}


@observe(name="retrieve-context", as_type="retriever", capture_input=False, capture_output=False)
def retrieve(message: str) -> list[str]:
    client = get_langfuse_client()
    client.update_current_span(
        input={"query": scrub_text(message)},
        metadata={"source": "mock-corpus"},
    )
    if STATE["tool_fail"]:
        raise RuntimeError("Vector store timeout")
    if STATE["rag_slow"]:
        time.sleep(2.5)
    lowered = message.lower()
    docs = ["No domain document matched. Use general fallback answer."]
    for key, matches in CORPUS.items():
        if key in lowered:
            docs = matches
            break
    client.update_current_span(
        output={"documents": docs, "doc_count": len(docs)},
        metadata={"source": "mock-corpus", "doc_count": len(docs)},
    )
    return docs
