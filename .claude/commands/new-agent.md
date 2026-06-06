---
name: /new-agent
description: "Scaffold a new worker agent with module, prompt v1, schema, tests, and eval stub"
---

# /new-agent

Scaffolds a complete new agent (e.g., sentiment_analyzer):

1. Create `src/agents/{role}_agent.py` with BaseAgent inheritance
2. Create `prompts/{role}/v1.md` system prompt
3. Update `prompts/registry.yaml` to register the new role
4. Update `src/orchestration/router.py` conditional edges
5. Create unit test in `tests/unit/test_agents/`
6. Create integration test in `tests/integration/`
7. Add eval dataset stub in `evals/datasets/`

**Usage**: `@claude /new-agent researcher_financial` → scaffolds a financial researcher agent

**Auto-generates**:
- Async agent class with prompt loading
- Registry entry with v1 (date, author)
- Router conditional edge
- Test fixtures
- Eval dataset template

**Next**: Edit `src/agents/{role}_agent.py`, refine prompt in `prompts/{role}/v1.md`, run `make eval` to test.
