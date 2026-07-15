# Tests

## Structure

- **`unit/`**: Pure logic tests, NO network/LLM calls (`test_prompt_loader.py`, `test_prompt_registry.py`, `test_tools/`)
- **`integration/`**: Real graph wiring, **hermetic** — no network (`test_trajectory.py`, `test_example.py`)
- **`fixtures/`**: Shared test data

> There is no VCR/cassette layer. `vcrpy` is not a dependency — integration tests fake the
> agent modules instead (see below). Older docstrings mentioning "vcr-recorded responses"
> describe an approach that was never built.

## Running Tests

```bash
# Unit tests only (fast)
uv run pytest tests/unit/

# Integration tests
uv run pytest tests/integration/

# All tests (unit + integration)
make test          # == uv run pytest tests/ -v

# With coverage
uv run pytest --cov=src/agentic_app tests/
```

Run through `uv run` (or `make test`) so the project env is synced first. On this machine
`UV_SYSTEM_CERTS=1` is required for uv to reach the network through the TLS-inspecting proxy.

## Writing Tests

### Unit Test

Hermetic by construction — the prompt tests touch only the filesystem + YAML, never importing
the heavy agent modules:

```python
def test_registry_roles_match_prompt_folders():
    registry = yaml.safe_load(pathlib.Path("prompts/registry.yaml").read_text())
    assert set(registry["roles"]) == {d.name for d in pathlib.Path("prompts").iterdir() if d.is_dir()}
```

### Integration Test (hermetic graph wiring)

`test_trajectory.py` injects fake agent node callables into `sys.modules` **before**
`graph.py` imports them, then compiles the real graph with a real `MemorySaver` +
`InMemoryStore`. This exercises the durable-checkpoint and Store-injection paths with no
network and no LLM calls. Use the `graph_factory` fixture:

```python
def test_evaluate_routes_to_deliver(graph_factory):
    """Real graph wiring, fake nodes — no network."""
    def evaluate_node(state: dict) -> dict:
        return {"grounding_score": 0.9}

    app, store = graph_factory(_fake_nodes(evaluate_node))
    final = app.invoke(
        {"ticker": "NVDA", "year": 2025, "quarter": 4},
        {"configurable": {"thread_id": "t1"}},
    )
    assert final["brief_markdown"]
```

Nodes are **sync** (`def`, not `async def`) — use `app.invoke`, not `await app.ainvoke`.

Any test that would hit a real API must be gated behind an env flag so `make test` never
phones home (see `RUN_LLM_JUDGE_TESTS` for the LLM-judge precedent).

## Fixtures

See `conftest.py` for:

- `fake_anthropic`: Mocked Anthropic client
- `in_memory_store`: In-memory store
- `frozen_clock`: Deterministic timestamps

`graph_factory` is local to `tests/integration/test_trajectory.py`.
