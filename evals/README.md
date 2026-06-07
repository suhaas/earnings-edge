# Evals

## Structure

- **`datasets/`**: Versioned eval sets (JSONL format)
- **`scorers/`**: Scoring functions (exact-match, LLM-as-judge, trajectory)
- **`suites/`**: Suite definitions (dataset → agent → scorer → threshold)
- **`run.py`**: Eval runner

## Running Evals

```bash
# Full suite
make eval

# Specific suite
python evals/run.py --suite researcher_baseline

# With verbose output
python evals/run.py --verbose

# Compare against baseline
python evals/run.py --baseline main
```

## Dataset Format

JSONL (one JSON per line):
```json
{"input": "Research Q3 earnings for MSFT", "expected_output": "MSFT Q3 revenue/EPS/guidance", "rubric": "Must include key metrics"}
```

## Scorers

Implement in `evals/scorers/`:
```python
def score_output(expected: str, actual: str) -> float:
    """Return 0.0-1.0 score."""
```

## Suites

Define in `evals/suites/`:
```yaml
suites:
  researcher_baseline:
    dataset: evals/datasets/researcher_qa.jsonl
    agent: researcher
    scorer: llm_judge
    threshold: 0.85
    timeout_per_case: 30
```

## CI/CD Integration

- **`eval-gate` job (in `ci.yml`)**: Runs `make eval` on every PR
- **Regression gate**: Fails PR if score < baseline (unless justified)
- **Report**: Attached to PR with delta + per-case scores
