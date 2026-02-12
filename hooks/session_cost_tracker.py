#!/usr/bin/env python3
"""
Claude Code SessionEnd hook: tracks token usage and cost per session.
Appends a row to ~/.claude/claude_session_costs.csv after each session.
"""

import csv
import json
import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path

CLAUDE_DIR = Path.home() / ".claude"
CSV_PATH = CLAUDE_DIR / "claude_session_costs.csv"
TOTAL_COST_PATH = CLAUDE_DIR / "total_cost.txt"

# Pricing per million tokens (USD) — https://platform.claude.com/docs/en/about-claude/pricing
# (model_id_substring): (input, output, cache_write_5m, cache_write_1h, cache_read)
PRICING = {
    "claude-opus-4-6":   (5,    25,   6.25,  10,   0.50),
    "claude-opus-4-5":   (5,    25,   6.25,  10,   0.50),
    "claude-opus-4-1":   (15,   75,   18.75, 30,   1.50),
    "claude-opus-4-":    (15,   75,   18.75, 30,   1.50),  # opus-4-20...
    "claude-sonnet-4-5": (3,    15,   3.75,  6,    0.30),
    "claude-sonnet-4-":  (3,    15,   3.75,  6,    0.30),  # sonnet-4-20...
    "claude-haiku-4-5":  (1,    5,    1.25,  2,    0.10),
    "claude-haiku-3-5":  (0.80, 4,    1.00,  1.60, 0.08),
    "claude-haiku-3":    (0.25, 1.25, 0.30,  0.50, 0.03),
}

# Fast mode (Opus 4.6): 6x standard pricing
FAST_PRICING = {
    "claude-opus-4-6": (30, 150, 37.50, 60, 3.00),
}


def get_pricing(model_id, service_tier="standard"):
    if not model_id:
        return PRICING["claude-sonnet-4-5"]  # fallback

    # Check fast mode first
    if service_tier != "standard":
        for prefix, prices in FAST_PRICING.items():
            if prefix in model_id:
                return prices

    # Match longest prefix first (sorted descending by key length)
    for prefix in sorted(PRICING.keys(), key=len, reverse=True):
        if prefix in model_id:
            return PRICING[prefix]

    return PRICING["claude-sonnet-4-5"]  # fallback


def process_transcript(transcript_path):
    """Parse the transcript JSONL and aggregate token usage and cost."""
    totals = {
        "input_tokens": 0,
        "output_tokens": 0,
        "cache_write_tokens": 0,
        "cache_read_tokens": 0,
        "api_calls": 0,
        "cost_usd": 0.0,
    }
    models_seen = set()
    session_id = None
    cwd = None
    first_ts = None
    last_ts = None

    with open(transcript_path, "r") as f:
        for line in f:
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue

            # Capture session metadata
            if not session_id and entry.get("sessionId"):
                session_id = entry["sessionId"]
            if not cwd and entry.get("cwd"):
                cwd = entry["cwd"]

            # Track timestamps
            ts = entry.get("timestamp")
            if ts:
                if not first_ts:
                    first_ts = ts
                last_ts = ts

            # Process assistant messages with usage data
            msg = entry.get("message", {})
            if not isinstance(msg, dict):
                continue

            usage = msg.get("usage")
            if not usage:
                continue

            model_id = msg.get("model", "")
            service_tier = usage.get("service_tier", "standard")
            models_seen.add(model_id)

            input_toks = usage.get("input_tokens", 0)
            output_toks = usage.get("output_tokens", 0)
            cache_creation_toks = usage.get("cache_creation_input_tokens", 0)
            cache_read_toks = usage.get("cache_read_input_tokens", 0)

            # Break down cache writes into 5m vs 1h
            cache_detail = usage.get("cache_creation", {})
            cache_5m = cache_detail.get("ephemeral_5m_input_tokens", cache_creation_toks)
            cache_1h = cache_detail.get("ephemeral_1h_input_tokens", 0)

            totals["input_tokens"] += input_toks
            totals["output_tokens"] += output_toks
            totals["cache_write_tokens"] += cache_creation_toks
            totals["cache_read_tokens"] += cache_read_toks
            totals["api_calls"] += 1

            # Calculate cost for this API call
            p_input, p_output, p_cw5m, p_cw1h, p_cr = get_pricing(model_id, service_tier)
            cost = (
                input_toks * p_input
                + output_toks * p_output
                + cache_5m * p_cw5m
                + cache_1h * p_cw1h
                + cache_read_toks * p_cr
            ) / 1_000_000
            totals["cost_usd"] += cost

    # Compute duration
    duration_min = None
    if first_ts and last_ts:
        try:
            t0 = datetime.fromisoformat(first_ts.replace("Z", "+00:00"))
            t1 = datetime.fromisoformat(last_ts.replace("Z", "+00:00"))
            duration_min = round((t1 - t0).total_seconds() / 60, 1)
        except Exception:
            pass

    return totals, models_seen, session_id, cwd, first_ts, duration_min


def main():
    hook_input = json.loads(sys.stdin.read())
    transcript_path = hook_input.get("transcript_path")

    if not transcript_path or not os.path.exists(transcript_path):
        return

    totals, models_seen, session_id, cwd, first_ts, duration_min = process_transcript(
        transcript_path
    )

    if totals["api_calls"] == 0:
        return

    # Determine timestamp for the row (Pacific Time)
    now = datetime.now(ZoneInfo("America/Los_Angeles"))
    session_date = now.strftime("%Y-%m-%d")
    session_time = now.strftime("%H:%M:%S")

    total_tokens = (
        totals["input_tokens"]
        + totals["output_tokens"]
        + totals["cache_write_tokens"]
        + totals["cache_read_tokens"]
    )

    row = {
        "date": session_date,
        "time": session_time,
        "session_id": session_id or "",
        "models": ";".join(sorted(models_seen)),
        "input_tokens": totals["input_tokens"],
        "output_tokens": totals["output_tokens"],
        "cache_write_tokens": totals["cache_write_tokens"],
        "cache_read_tokens": totals["cache_read_tokens"],
        "total_tokens": total_tokens,
        "api_calls": totals["api_calls"],
        "cost_usd": round(totals["cost_usd"], 4),
        "duration_min": duration_min if duration_min is not None else "",
        "working_dir": cwd or "",
    }

    fieldnames = list(row.keys())
    write_header = not CSV_PATH.exists()

    with open(CSV_PATH, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if write_header:
            writer.writeheader()
        writer.writerow(row)

    # Update running total
    prev_total = 0.0
    if TOTAL_COST_PATH.exists():
        try:
            prev_total = float(TOTAL_COST_PATH.read_text().strip())
        except (ValueError, OSError):
            pass
    new_total = prev_total + row["cost_usd"]
    TOTAL_COST_PATH.write_text(f"{new_total:.4f}\n")


if __name__ == "__main__":
    main()
