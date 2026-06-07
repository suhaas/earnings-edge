---
name: evals-instructions
applyTo: ["evals/**", "tests/unit/**", "tests/integration/**"]
description: "Rules for testing and evals: no network in unit tests, eval datasets versioned, scorers deterministic. Use when: writing tests, adding eval cases, updating eval suites."
---

# Testing & Evaluation Guidelines

## Unit Tests

- **Location**: `tests/unit/`
- **CRITICAL**: NO network calls, NO LLM calls, NO side effects
- **Mocking**: Use fixtures in `conftest.py` (fake Anthropic, in-memory store, frozen clock)
- **Run**: `pytest tests/unit/` or `make test`

### Example
```python
def test_tool_error_wrapping(fake_anthropic):
    """Unit test with mocked client."""
    from agentic_app.tools.web_search import search
    from agentic_app.tools.schemas import ToolError
    
    # Mock or use fake fixture
    with pytest.raises(ToolError) as exc_info:
        search(query="invalid")
    
    assert exc_info.value.category == "validation"
```

## Integration Tests

- **Location**: `tests/integration/`
- **Real wiring**: LangGraph topology is real; LLM responses are vcr-style recorded (deterministic)
- **Setup**: Tests replay captured traces so results are reproducible
- **Run**: `pytest tests/integration/` or `make test`

### Example
```python
@pytest.mark.integration
async def test_researcher_agent_e2e(graph_with_recorded_responses):
    """Integration test with vcr-recorded LLM responses."""
    state = await graph_with_recorded_responses.ainvoke({
        "messages": [HumanMessage(content="Research earnings for AAPL")],
    })
    assert len(state["messages"]) > 1
    assert "Apple" in state["messages"][-1].content
```

## Eval Suites

### Datasets
- **Location**: `evals/datasets/`
- **Format**: JSONL (one JSON object per line)
- **Versioning**: Immutable; new dataset = new file (`v1.jsonl`, `v2.jsonl`)
- **Content**: `{"input": ..., "expected_output": ..., "rubric": ...}`

Example `evals/datasets/researcher_qa.jsonl`:
```json
{"input": "Research Q3 earnings for Microsoft", "expected_output": "MSFT Q3 revenue, EPS, guidance", "rubric": "Must extract key metrics"}
{"input": "Find analyst sentiment on Tesla", "expected_output": "Analyst ratings, target prices", "rubric": "Sentiment signals required"}
```

### Scorers
- **Location**: `evals/scorers/`
- **Deterministic**: No randomness, same input → same score
- **Types**:
  - `llm_judge.py`: LLM-as-judge (use recorded responses for determinism)
  - `trajectory.py`: Tool-call sequence matching
  - `exact_match.py`: String exact match

### Suites
- **Location**: `evals/suites/`
- **Definition**: YAML that binds dataset → agent → scorer → threshold

Example `evals/suites/regression.yaml`:
```yaml
suites:
  researcher_baseline:
    dataset: evals/datasets/researcher_qa.jsonl
    agent: researcher_agent
    scorer: llm_judge
    threshold: 0.85  # 85% of cases must pass
    timeout_per_case: 30s
```

### Running Evals
```bash
# Local eval run
make eval

# CI/CD eval gate (runs on every PR)
# See: .github/workflows/ci.yml (eval-gate job)
```

## Regression Gate

- **CI/CD**: the `eval-gate` job in `ci.yml` runs on every PR
- **Baseline**: Eval scores from `main` branch become the baseline
- **Failure**: If score < baseline, PR fails (must fix or justify regression)
- **Metadata**: Eval reports attached to PR (JSON + summary)

## Fixtures & Mocking

See `tests/conftest.py` for:
- `fake_anthropic`: Fake Anthropic client (no API calls)
- `in_memory_store`: Vector DB for tests
- `frozen_clock`: Deterministic timestamps

```python
@pytest.fixture
def fake_anthropic():
    """Returns a mocked Anthropic client for tests."""
    # Implementation in conftest.py
```
