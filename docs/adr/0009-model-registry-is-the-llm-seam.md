# ADR-0009: The Model Registry Is the LLM Seam

**Status**: Accepted
**Date**: 2026-07-15

## Context

Three separate needs converge on the same place in the code:

1. **Model routing.** `config/models.py` holds a `ModelRegistry` with **zero callers**. Four agents
   hardcode their model inline. Until 2026-07-15 the registry pinned three model IDs that all
   **404** — nobody noticed, because dead code cannot fail.
2. **Retry / circuit breaker.** `AGENTS.md:285-288` (= `CLAUDE.md` = `copilot-instructions.md`):
   *"No `llm/retry.py` and no circuit breaker exist ... Intended: exponential backoff on
   `RateLimitError`, fast-fail after N failures."* The richer spec is the deleted
   `skills/api_integration/SKILL.md`: *"Retries: Exponential backoff with jitter / Rate limits: Honor
   X-RateLimit headers, circuit breaker."*
3. **Tracing.** `AGENTS.md:294-296` names a **`@traced` decorator** that was never written.

All three want to wrap the same thing: the construction and invocation of a model.

**The call sites are not uniform.** Four Anthropic sites, three construction idioms:

| Site | Idiom |
|---|---|
| `kpi_agent.py:18` | `ChatAnthropic(model=…, temperature=0)` → `.with_structured_output(...)` |
| `synthesis_agent.py:18` | `ChatAnthropic(model=…, temperature=0.2)` |
| `delivery_agent.py:29` | `ChatAnthropic(model=…, temperature=0)` |
| `evaluation_agent.py:19` | `create_llm_as_judge(model="anthropic:claude-sonnet-4-5", …)` — **provider-prefixed string** |

Plus a fifth, non-Anthropic model: `sentiment_agent.py:48` runs `pipeline("text-classification",
model="ProsusAI/finbert")` — a local HuggingFace pipeline with no API, no tier, no temperature.

**A hard constraint shapes the design.** `claude-sonnet-5` and `claude-opus-4-8` **reject
`temperature` with a 400** — any value, including `0`. `claude-sonnet-4-5` and `claude-haiku-4-5`
accept it. So model choice and sampling parameters are *coupled*, and a registry returning a bare
`str` cannot express that.

**`llm/` is vestigial.** `llm/anthropic_client.py` is a 10-line stub with zero callers;
`AGENTS.md:133` already labels it "STUB (agents call ChatAnthropic directly)". Adding `retry.py`
beside a dead client would be building on sand.

## Decision

1. **`config/models.py` is the seam.** Two-level: **role → tier → model**.
   `resolve(role) -> ModelSpec`. Agents ask by *role* (what work they do), not by model or tier.
2. **Storage is a Python literal, not YAML** — a deliberate divergence from `PromptLoader`, which
   this otherwise mirrors (module singleton, typed error, constructor injection, dict cache).
3. **Unknown role raises `ModelError`.** The old `get()` silently defaulted to `balanced`.
4. **`temperature` is per-role, reconciled against a per-tier `accepts_temperature`.** When a tier
   rejects it, the kwarg is **absent** from the constructor call — not passed as `None`.
5. **`ModelSpec` is a frozen dataclass** carrying `id`, `temperature`, a `qualified_id` property
   (`anthropic:…`) for openevals, and `chat_kwargs()` for `ChatAnthropic`.
6. **FinBERT stays out.** It is a local pipeline, not an Anthropic API model.
7. **Delete `llm/anthropic_client.py`.** `llm/retry.py` is scoped to a **circuit breaker only** —
   the Anthropic SDK already ships `max_retries` with exponential backoff.
8. **Third-party retry is a different problem.** yfinance 429s and SEC's 10 req/s limit occur at
   `kpi_agent._consensus` and `ingestion_agent`, not at an LLM call. They do **not** belong in
   `llm/`. Track separately.

**Wiring is behaviour-neutral only because `balanced` is pinned to `claude-sonnet-4-5`** — the model
the agents run today. Upgrading to `claude-sonnet-5` is a *separate* decision with a *separate* PR.

## Rationale

- **Two levels earn their keep.** One level (tier → model) still leaves every agent hardcoding
  *which tier*. Two levels make re-tiering one agent a registry edit.
- **The tier boundary is exactly where `accepts_temperature` belongs** — it is a property of the
  model, not of the role. That reconciliation turns the Sonnet 5 upgrade into a two-line registry
  change whose golden test goes red, forcing conscious acceptance of the determinism loss.
- **Python literal over YAML**: the data is 7 scalars; mypy checks a dict but not `yaml.safe_load`
  (which returns `Any` under `strict`); a missing key fails at build time rather than raising
  mid-graph after ingestion has already burned network I/O. And placement is a dead end —
  `test_prompt_registry.py` globs subdirectories of `prompts/`, so a registry YAML cannot live there;
  a repo-root YAML would need `PromptLoader`'s `parents[3]` trick, which **already only works from a
  source checkout** (`prompts/` is not shipped in the wheel). Replicating a latent bug for 7 scalars
  is a bad trade. **No drift guard is lost**: the guard is `roles ⊆ agent files`, which asserts
  identically against a literal.
- **Raising beats defaulting.** Silent default-to-`balanced` is *precisely* the failure mode that hid
  three dead IDs. All call sites pass literals, so raising costs nothing and turns a typo into a loud
  error plus red CI.
- **Absence over `None`.** `langchain-anthropic` happens to filter `None` params, but relying on that
  leans on an internal. Absence is provable in our own test.

## Alternatives Considered

- **Return a bare `str`**: rejected — cannot carry `temperature` or the `anthropic:` prefix, so the
  evaluation site and the C5 constraint both leak back into the agents.
- **Role-keyed YAML mirroring `PromptLoader` exactly**: rejected — see placement dead end above.
  Revisit if pins must change without a deploy (per-env pinning, ops rollback).
- **Tier-keyed only** (`get("balanced")`, as originally briefed): rejected — every agent still
  hardcodes its tier *and* its temperature *and* the prefix; three of the four coupling problems
  survive.
- **Pydantic `ModelSpec`**: rejected — Pydantic validates *untrusted* input crossing a boundary
  (which is why `state.py` uses it). This is trusted, statically-typed, in-process data.
- **Prefix as per-role config**: rejected — every tier is Anthropic by construction. It is a
  *rendering* of the ID, not a knob. If a second provider appears, `provider` moves onto `Tier`.
- **Put retry in `llm/retry.py` covering both LLM and provider calls**: rejected — different call
  sites, different libraries, different failure semantics. One module cannot honestly own both.
- **Wire the registry and upgrade the model together**: rejected — mixes a mechanical refactor with a
  behaviour change. If evals move, you cannot tell which caused it.

## Consequences

- Four agent call sites gain `from agentic_app.config.models import model_registry`. The lookup must
  live **inside the agent modules** — `tests/integration/test_trajectory.py` fakes those away via
  `sys.modules`, and a new top-level import in `graph.py` would execute for real.
- The three `# type: ignore[call-arg]` comments on `ChatAnthropic(...)` become **unused** once the
  call is `**spec.chat_kwargs()` — and `strict` makes an unused ignore an *error*. Verify with
  `make lint`, not by eye.
- `ModelRegistry.get()` is deleted. Any future caller must use `resolve()`.
- `config/models.py` must **not** import `config/settings.py` (which raises at import) or
  `config/logging.py` (which calls `structlog.configure()` at import). It stays inert: stdlib only.
- Re-pinning `balanced` from `claude-sonnet-5` → `claude-sonnet-4-5` will read as a downgrade in
  review. It is not: it decouples *wire the registry* from *change which model runs*.
- A fifth hardcoded model string exists in `tests/integration/test_trajectory.py:212`
  (`"anthropic:claude-sonnet-4-5"`). It is deliberately left alone — it is `skipif`-gated, and
  coupling a test's judge choice to production role config would be worse than the duplication.
