---
name: code_execution
description: "Sandboxed code execution for data processing, analysis, and calculations. Use when: agents need to run Python, query BigQuery, process files, or perform numerical reasoning in a controlled environment."
---

# Code Execution Skill

This skill enables agents to safely execute code in a sandboxed environment for data analysis, transformations, and complex calculations.

## When to Use

- Performing statistical analysis on earnings data
- Running SQL queries against BigQuery or databases
- Processing and transforming structured data
- Building financial models or forecasts
- Generating visualizations and reports
- Debugging tool outputs or data inconsistencies

## Sandboxing & Limits

- **Environment**: Docker container or subprocess with resource limits
- **Timeout**: 30 seconds max per execution
- **Memory**: 512MB limit
- **Disk**: No persistence; each run is isolated
- **Network**: Outbound to approved APIs only (configured in settings)
- **File I/O**: Scoped to `/tmp/{run_id}/` directory; no access to host

## Tool: code_exec

```python
# Example: code_exec(code="...", language="python")
result = await code_exec(
    code="""
import pandas as pd
data = {'ticker': ['AAPL', 'MSFT'], 'revenue': [100, 120]}
df = pd.DataFrame(data)
print(df.describe())
""",
    language="python"
)
```

**Returns**: `{"stdout": "...", "stderr": "...", "exit_code": 0}`

## Available Libraries

Pre-installed:
- `pandas`: Data manipulation
- `numpy`: Numerical computing
- `scipy`: Scientific computing
- `matplotlib`, `seaborn`: Plotting
- `sqlalchemy`: ORM + query building
- `requests`: HTTP client
- `json`, `csv`: Parsing

Custom earnings-specific (if available):
- `yfinance`: Yahoo Finance API wrapper
- `sec-edgar`: SEC EDGAR filing scraper
- `alpaca-py`: Alpaca broker API

## Safe Patterns

### ✅ DO
```python
# Validate inputs before processing
if not isinstance(ticker, str) or len(ticker) > 5:
    raise ValueError(f"Invalid ticker: {ticker}")

# Use parameterized queries to avoid injection
query = "SELECT * FROM earnings WHERE ticker = %s"
df = pd.read_sql(query, conn, params=[ticker])

# Handle errors gracefully
try:
    result = calculate_ratio(data)
except ZeroDivisionError:
    result = None
```

### ❌ DON'T
```python
# Don't use eval() or exec() on untrusted input
eval(user_code)  # NEVER!

# Don't hardcode credentials
api_key = "sk-abc123"  # NEVER!

# Don't assume data validity
df['revenue'] / df['expenses']  # What if expenses is 0?

# Don't run unbounded loops
while True:  # Will hit timeout
    ...
```

## Output Format

Always structure results:
```json
{
  "type": "analysis|error|visualization",
  "summary": "Brief result description",
  "data": {...},
  "timestamp": "2026-02-05T10:30:00Z",
  "code_hash": "sha256:..."
}
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Timeout (30s) | Reduce data volume; use sampling; move to async queries |
| Memory exceeded | Process in chunks; delete large objects; use generators |
| ImportError | Library not installed; request in PR or use `subprocess` + pip |
| No output | Add explicit `print()` statements; check stderr |

## Security Checklist

- [ ] No hardcoded credentials
- [ ] No eval/exec on user input
- [ ] Parameterized SQL queries
- [ ] Error handling for all I/O
- [ ] Timeout-safe loops
- [ ] File cleanup after execution

## Next Steps

See `AGENTS.md` → Coder Agent role for how this skill integrates with the graph.
