"""Render the six-panel lab dashboard from data/logs.jsonl and config/dashboard.yaml."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]


def percentile(values: list[float], p: int) -> float:
    if not values:
        return 0.0
    items = sorted(values)
    idx = max(0, min(len(items) - 1, round((p / 100) * len(items) + 0.5) - 1))
    return float(items[idx])


def parse_ts(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def load_rows(path: Path, window_minutes: int) -> list[dict]:
    rows = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    stamped = [row for row in rows if row.get("ts")]
    if not stamped:
        return rows
    latest = max(parse_ts(row["ts"]) for row in stamped)
    start = latest - timedelta(minutes=window_minutes)
    return [row for row in stamped if parse_ts(row["ts"]) >= start]


def panel_values(rows: list[dict]) -> dict[str, dict]:
    received = [row for row in rows if row.get("event") == "request_received"]
    sent = [row for row in rows if row.get("event") == "response_sent"]
    failed = [row for row in rows if row.get("event") == "request_failed"]
    tool_rows = [row for row in rows if row.get("tool_success") is not None]
    tool_ok = sum(1 for row in tool_rows if row.get("tool_success") is True)

    by_minute_cost: dict[str, float] = defaultdict(float)
    by_minute_traffic: dict[str, int] = defaultdict(int)
    for row in sent:
        minute = parse_ts(row["ts"]).strftime("%H:%M")
        by_minute_cost[minute] += float(row.get("cost_usd") or 0)
    for row in received:
        minute = parse_ts(row["ts"]).strftime("%H:%M")
        by_minute_traffic[minute] += 1

    minutes = sorted(set(by_minute_cost) | set(by_minute_traffic))
    error_rate = (len(failed) / len(received) * 100) if received else 0.0
    retrieval = (tool_ok / len(tool_rows) * 100) if tool_rows else 0.0
    window_minutes = max(1, len(minutes))

    return {
        "latency": {
            "P50 latency": percentile([float(row["latency_ms"]) for row in sent], 50),
            "P95 latency": percentile([float(row["latency_ms"]) for row in sent], 95),
            "P99 latency": percentile([float(row["latency_ms"]) for row in sent], 99),
            "TTFT P95": percentile([float(row["ttft_ms"]) for row in sent], 95),
        },
        "traffic": {
            "Count": float(len(received)),
            "Requests per minute": len(received) / window_minutes,
            "series": {minute: by_minute_traffic[minute] for minute in minutes},
        },
        "errors": {
            "Error rate": error_rate,
            "Retrieval success": retrieval,
            "breakdown": dict(Counter(row.get("error_type") or "none" for row in failed)),
        },
        "cost": {
            "Total": sum(float(row.get("cost_usd") or 0) for row in sent),
            "series": {minute: by_minute_cost[minute] for minute in minutes},
        },
        "tokens": {
            "Input tokens": float(sum(int(row.get("tokens_in") or 0) for row in sent)),
            "Output tokens": float(sum(int(row.get("tokens_out") or 0) for row in sent)),
        },
        "quality": {
            "Mean quality": (
                sum(float(row.get("quality_score") or 0) for row in sent) / len(sent) if sent else 0.0
            ),
        },
    }


def status(value: float, operator: str, threshold: float) -> str:
    ok = value <= threshold if operator == "lte" else value >= threshold
    return "ok" if ok else "breach"


def render(config: dict, values: dict[str, dict], row_count: int) -> str:
    dashboard = config["dashboard"]
    cards = []
    for panel in dashboard["panels"]:
        panel_id = panel["id"]
        stats = values[panel_id]
        threshold = panel["threshold"]
        headline_key = {
            "latency": "P95 latency",
            "traffic": "Requests per minute",
            "errors": "Error rate",
            "cost": "Total",
            "tokens": "Input tokens",
            "quality": "Mean quality",
        }[panel_id]
        headline = stats[headline_key]
        compared = headline
        if panel_id == "tokens":
            compared = stats["Input tokens"] + stats["Output tokens"]
        tone = status(float(compared), threshold["operator"], float(threshold["value"]))
        rows_html = []
        for key, value in stats.items():
            if key in {"series", "breakdown"}:
                continue
            number = f"{value:.4f}" if isinstance(value, float) and value < 10 else f"{value:.2f}"
            rows_html.append(f"<tr><td>{key}</td><td>{number}</td></tr>")
        extra = ""
        if panel_id == "errors":
            extra = f"<p class='note'>Error breakdown: {stats['breakdown'] or '{}'}</p>"
        cards.append(
            f"""
            <section class="card {tone}">
              <h2>{panel['title']}</h2>
              <p class="meta">{panel_id} · unit {panel['unit']} · threshold {threshold['aggregation']} {threshold['operator']} {threshold['value']}</p>
              <p class="headline">{headline:.4f} <span>{panel['unit']}</span></p>
              <table>{''.join(rows_html)}</table>
              {extra}
            </section>
            """
        )
    return f"""<!DOCTYPE html>
<html lang="vi">
<head>
  <meta charset="utf-8" />
  <title>{dashboard['title']}</title>
  <style>
    body {{ font-family: Segoe UI, sans-serif; margin: 8px 12px; background: #0f172a; color: #e2e8f0; }}
    h1 {{ margin: 0 0 2px; font-size: 22px; }}
    .range {{ color: #94a3b8; margin: 0 0 8px; font-size: 13px; }}
    .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }}
    .card {{ background: #1e293b; border-radius: 10px; padding: 8px 10px; border-top: 4px solid #22c55e; }}
    .card.breach {{ border-top-color: #ef4444; }}
    h2 {{ margin: 0 0 2px; font-size: 15px; }}
    .meta, .note {{ color: #94a3b8; font-size: 11px; margin: 2px 0; }}
    .headline {{ font-size: 20px; margin: 4px 0; }}
    .headline span {{ font-size: 12px; color: #94a3b8; }}
    table {{ width: 100%; border-collapse: collapse; }}
    td {{ padding: 2px 0; border-bottom: 1px solid #334155; font-size: 13px; }}
    td:last-child {{ text-align: right; }}
  </style>
</head>
<body>
  <h1>{dashboard['title']}</h1>
  <p class="range">Time range: last {dashboard['time_range_minutes']} minutes · refresh {dashboard['refresh_seconds']}s · source data/logs.jsonl · {row_count} log rows in window</p>
  <div class="grid">{''.join(cards)}</div>
</body>
</html>
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Render the Day 13 six-panel dashboard")
    parser.add_argument("--logs", type=Path, default=REPO_ROOT / "data" / "logs.jsonl")
    parser.add_argument("--config", type=Path, default=REPO_ROOT / "config" / "dashboard.yaml")
    parser.add_argument(
        "--output",
        type=Path,
        default=REPO_ROOT / "submission" / "evidence" / "dashboard.html",
    )
    args = parser.parse_args()
    config = yaml.safe_load(args.config.read_text(encoding="utf-8"))
    window = int(config["dashboard"]["time_range_minutes"])
    rows = load_rows(args.logs, window)
    html = render(config, panel_values(rows), len(rows))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(html, encoding="utf-8")
    print(f"Wrote {args.output} from {len(rows)} log rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
