# Tests

## Structure

- **`unit/`**: Pure logic tests, NO network/LLM calls, mocked fixtures
- **`integration/`**: Real graph wiring with vcr-style recorded LLM responses
- **`fixtures/`**: Shared test data

## Running Tests

```bash
# Unit tests only (fast)
pytest tests/unit/

# Integration tests
pytest tests/integration/

# All tests (unit + integration)
pytest tests/

# With coverage
pytest --cov=src/agentic_app tests/
```

## Writing Tests

### Unit Test (Mocked)
```python
def test_tool_error_wrapping(fake_anthropic):
    """No network, mocked client."""
    from agentic_app.tools.web_search import search
    
    result = search(query="AAPL earnings")
    assert "revenue" in result
```

### Integration Test (VCR Replay)
```python
@pytest.mark.integration
async def test_researcher_e2e(graph_with_recorded_responses):
    """Real graph wiring, recorded LLM responses."""
    state = await graph_with_recorded_responses.ainvoke({
        "messages": [HumanMessage(content="Research earnings")],
    })
    assert len(state["messages"]) > 1
```

## Fixtures

See `conftest.py` for:
- `fake_anthropic`: Mocked Anthropic client
- `in_memory_store`: In-memory vector DB
- `frozen_clock`: Deterministic timestamps
