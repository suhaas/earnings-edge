---
name: /eval
description: "Run eval suite and report regressions vs. main baseline"
---

# /eval

Runs the agent evaluation suite and compares scores against the main branch baseline.

**Usage**: `@claude /eval` → runs full suite, `@claude /eval researcher_qa` → runs specific suite

**Output**:
- Pass/fail for each test case
- Regression detection (if score < baseline)
- Per-agent metrics (tokens, latency, tool calls)
- JSON report for CI attachment

**Examples**:
- `/eval` — Full regression suite
- `/eval researcher_qa` — Researcher agent only
- `/eval --verbose` — With detailed traces

**Next**: If regression detected, debug with `scripts/replay_trace.py <trace_id>` or update prompts.
