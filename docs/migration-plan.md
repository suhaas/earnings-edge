# earnings-edge — Refactoring & Migration Plan

## Context

Today's session began as a session-recovery question and ended by uncovering that this repo's
documentation described **a different application** than the one that runs: a supervisor routing to
researcher/analyst/coder over `src/orchestration/` and `src/rag/` modules that do not exist. Six docs
were corrected on `fix/docs-drift-and-dead-model-ids`. That fix exposed the deeper problem this plan
addresses:

- **`config/models.py` pinned three model IDs that 404.** Nothing broke, because `model_registry` has
  **zero callers** — the agents hardcode `ChatAnthropic(model="claude-sonnet-4-5")` inline.
- **8 of 18 modules have no importers**: `config/settings.py`, `config/logging.py`, `config/models.py`,
  `tools/registry.py`, `tools/schemas.py`, `llm/anthropic_client.py`, `agents/base.py`, `api/app.py`.
- Neither failure could be caught, because **markdown can't fail a test and dead code can't raise**.

**Root cause — two archaeological layers.** Commit `4805dc9` laid down a generic agentic scaffold
(supervisor/researcher/critic, RAG, MCP, memory, observability). Commit `94ede9c` built the real
earnings pipeline and deleted the scaffold's prompts and skills — but left every stub package, ADR,
runbook, and eval in place. Commit `5ed85a8` swept the agent-facing docs and stopped there.
**This plan is, in large part, finishing `5ed85a8`.**

**Intended outcome:** every module has a caller, every doc matches the code, the two live bugs are
fixed, and drift is guarded by tests rather than vigilance.

---

## The finding that shapes everything

The brief assumed the empty packages "represent deliberate architectural intent." Research says that
holds for **one of five**:

| Stub | Verdict | Evidence |
|---|---|---|
| `rag/` | **Delete** | Real spec exists, but **0 of 13 domain skills reference retrieval**. One earnings call fits in context (`kpi_agent` passes `text[:18000]`). Cross-quarter need is served by the Store. |
| `mcp/` | **Delete** | **Zero** intent. No ADR, skill, prompt, or consumer. `edgartools-mcp` is an accident of a dep chosen for ingestion. `.vscode/mcp.json` names 3 servers, none installed. |
| `memory/` | **Delete** | **Not unbuilt — superseded.** `94ede9c` deleted `memory_management` and wired `BaseStore` end-to-end in the same commit. Done, under a different name. |
| `observability/` | **Build** | Precisely specced: `@traced` decorator, OTel init, 4 Prometheus counters. A 3-service pipeline is provisioned with **zero producers**. |
| `llm/retry.py` | **Build (narrowed)** | Real, but conflates LLM vs data-provider rate limits; Anthropic SDK already ships `max_retries`. The genuinely missing piece is the circuit breaker. |

### Decisions taken (this session)

1. **Posture:** converge on the real app — delete what the domain never adopted.
2. **Registry shape:** role → tier → model (two-level).
3. **Model upgrade:** separate from wiring. Pin `balanced` to `claude-sonnet-4-5` so wiring is a
   **true no-op**; upgrade to Sonnet 5 later with an eval baseline.
4. **Persistence bug:** fix early.

### Four live bugs

- **B-1 `sentiment_surprise` is permanently 0.0 on the default config.** The Store is durable only on
  Postgres; SQLite gives `InMemoryStore`. `sentiment_agent` needs ≥2 prior quarters and finds 0, so the
  0.20-weighted tone term is always zero and `confidence` is capped — **scores are wrong, not just
  unavailable**. Receipt: `examples/AAPL-Q1-FY2025-brief.md` → "n_quarters = 0".
  **`langgraph.store.sqlite.SqliteStore` is already installed** — fixable at zero dependency cost.
- **B-2 The live delivery prompt instructs the agent to "escalate to the Critic"** and use exponential
  backoff. No Critic role exists; no backoff facility exists. `prompts/shared/tool_use_policy.md:14` →
  `prompts/delivery/v1.md:27` → `delivery_agent.py:58`. The only *user-visible* fossil.
- **B-3 All six agents have 0% unit coverage — 215 statements of untested business logic.** Verified:
  `kpi_agent` 46/46 missed, `ingestion_agent` 47/47, `sentiment_agent` 41/41, `delivery_agent` 37/37,
  `synthesis_agent` 25/25, `evaluation_agent` 19/19. **`test_trajectory.py` fakes every one of them away**,
  so it proves the graph *wiring* and nothing about the logic. The entire scoring model (weights, `_z` clamp,
  `tanh`), `_pct` surprise math, `_ratios` hedging, and `guidance_direction` thresholds are pure functions —
  trivially testable, never tested. `addopts` measures coverage with **no `--cov-fail-under`**, so 32% never
  fails. *This is the largest correctness risk in the repo and the refactor's biggest hazard: **there is no
  net beneath Phase 1's "behaviour-neutral" claim** beyond `make eval`, which is itself a no-op (B-4).*
- **B-4 Prompt changes have no enforced review, and the gate that should catch them is decorative.**
  Three independent no-ops compound: `evals/run.py` has `PLACEHOLDER = True` → always exit 0;
  `prompt-diff.yml` ends `exit 0  # Let eval gate decide`; `.github/CODEOWNERS` names `@owner` /
  `@ai-eng-team`, which are **placeholders** — GitHub silently ignores rules referencing non-existent
  users/teams, so the file is inert. Yet `CLAUDE.md:138` claims *"Human review: Check CODEOWNERS"*.
  **Net: a prompt can regress agent quality and reach `main` with zero human or automated gate.**
  (Note: `agents/` *does* match `src/agentic_app/agents/` — CODEOWNERS uses gitignore-style patterns, so an
  unanchored pattern matches at any depth. The file is inert because of the placeholders, not the paths.
  Separately `prompts/` **over**-matches: it catches both `prompts/` and `src/agentic_app/prompts/`.)

---

## DELIVERABLE 1 — Phased roadmap

```text
PHASE 0 · RECORD          (docs only · low complexity · no code risk)
  ADR-0005 memory = BaseStore          ─┐
  ADR-0006 persistence (amends 0001)   ─┼─ all parallel, no deps
  ADR-0007 RAG not required            ─┤
  ADR-0008 supersede ADR-0002          ─┤
  ADR-0009 llm/ seam                   ─┤
  ADR-0010 observability surface       ─┤
  ADR-0011 MCP deferred                ─┘
        │
        ▼
PHASE 0.5 · BUILD THE NET  ⚠️ NEW — do this FIRST (high value · medium)
  #14 unit-test the 6 agents + --cov-fail-under      (bug B-3)
       └─ WHY FIRST: Phase 1 claims "behaviour-neutral", gated on `make eval`
          being unchanged. But make eval is a PLACEHOLDER that always passes.
          Today there is NO net beneath the refactor. Build it before you lean on it.
        │
        ▼
PHASE 1 · SEAMS           (behaviour-NEUTRAL refactors · medium · eval must not move)
  #1 model registry (role→tier) + wire 4 sites   ← ADR-0009, net from #14
  #2 checkpoint.py extraction + orphan fix       ← ADR-0006, net from #14
       (independent — ship in either order)
        │
        ▼
PHASE 2 · FIX             (behaviour CHANGE · medium)
  #3 SqliteStore swap → fixes B-1                ← #2
  #4 tool_use_policy v2 → fixes B-2              (independent)
  #18 uniform error-as-state + ingestion swallow ← #14, after #1
        │
        ▼
PHASE 3 · DELETE          (subtractive · low risk, wide diff)
  #5 delete mcp/ memory/ rag/ tools/ api/ llm/anthropic_client.py
  #6 settings.py — wire or delete (import-time crash)
        │
        ▼
PHASE 4 · BUILD           (additive · high complexity)
  #7 observability/tracing.py — OTel init + @traced   ← ADR-0010
  #8 llm/retry.py — circuit breaker                   ← ADR-0009, #1
  #9 prometheus.yml scrape fix + metrics.py           ← #7, #11
        │
        ▼
PHASE 5 · RAISE           (behaviour CHANGE · needs baseline)
  #10 model upgrade → sonnet-5, drop temperature      ← #1, #11
  #11 evals: flip PLACEHOLDER=False                   ← ADR-0004 pre-authorises
        │
        ▼
PHASE 6 · SWEEP           (docs + hygiene · low)
  #12 runbooks · skills/README · .github/instructions · evals fossils
  #13 drift guards: docs-path test + dead-module check + model liveness
  #15 agent-facing commands (.claude/commands, .github/prompts, mcp.json)
       └─ #15's new-agent.md MUST ship WITH #5 (it cites BaseAgent, which #5 deletes)
  #16 governance: CODEOWNERS + prompt-diff + eval no-ops   (bug B-4)  ← #11
  #17 CI/release/packaging hygiene
```

**Dependency rule:** Phase 1 must land with **zero eval movement** — that's the proof the refactor was
mechanical. **But `make eval` is currently a no-op**, so #14 (agent unit tests) is what actually makes that
proof mean anything. Phase 5 is the only place behaviour is allowed to change, and it needs #11 first.

**Two ordering constraints added after review:**
- **#14 moves to the front.** Without it, "behaviour-neutral" is an unverifiable claim.
- **#15's `new-agent.md` fix must ship in the same PR as #5.** #5 deletes `base.py`; the command tells
  agents to inherit from it. Landing #5 alone leaves an actively harmful instruction.

**Complexity:** Phase 0 ≈ 1 day · **Phase 0.5 ≈ 2 days** · Phase 1 ≈ 2 days · Phase 2 ≈ 1 day ·
Phase 3 ≈ 1 day · Phase 4 ≈ 3–4 days · Phase 5 ≈ 2–3 days (eval-bound) · Phase 6 ≈ 2 days.

---

## Hard constraints (verified — violating these breaks the build)

| # | Constraint | Consequence |
|---|---|---|
| **C1** | `tests/integration/test_trajectory.py` fakes the 6 agent modules via `sys.modules`, then re-imports `graph.py`. | `graph.py`'s six `from agentic_app.agents.X import <node>` lines must stay **byte-identical**. Any new top-level import in `graph.py` executes for real. Registry lookups go **inside agent modules**, never in `graph.py`. `agents/__init__.py` must stay inert. |
| **C2** | `config/settings.py` raises `ValidationError` **at import** (3 required fields; `settings = Settings()` at module level). Zero importers today — that's why tests pass. | Nothing reachable from `graph.py` may import it. `config/logging.py` likewise calls `structlog.configure()` at import. |
| **C3** | `main.py`'s `graph.invoke(...)` sits **inside** `with ExitStack()`. | Savers are context managers; hoisting the invoke out is use-after-close. `checkpoint.py` must preserve this. |
| **C4** | 4 Anthropic call sites, **3 construction idioms** + 1 non-Anthropic. | `evaluation_agent` needs `"anthropic:"`-prefixed string; FinBERT must stay out of the registry. |
| **C5** | `claude-sonnet-5` / `claude-opus-4-8` reject `temperature` (**any** value incl. 0) with 400. | Temperature must be per-role data and **omittable** per tier. |
| **C6** | mypy `strict = true`, `ignore_missing_imports = false` **globally**; ruff selects `TRY`. | Every new untyped dep needs a `pyproject` override. `BaseCheckpointSaver` is generic → `BaseCheckpointSaver[Any]`. |
| **C7** | `prompts/loader.py` is the house pattern to mirror. | Module singleton, `resolve(role)`, typed error with valid keys listed, constructor injection, dict cache. |
| **C8** | `tests/unit/test_prompt_registry.py` asserts 3-way set equality: `agents/*_agent.py` ↔ `registry.yaml` roles ↔ `prompts/<role>/` dirs. | No new `*_agent.py`. A models YAML must **not** live under `prompts/`. |

---

## DELIVERABLE 2 — GitHub issue drafts

> Reusable assets: `src/agentic_app/prompts/loader.py` (the pattern to mirror),
> `tests/unit/test_prompt_registry.py` (the drift-guard pattern to replicate),
> `docs/adr/0004-consolidate-eval-gate-into-ci.md` (the ADR house style — names the drift, the failure
> mode, the rejected alternatives, and the exact flag to flip later).

---

### Issue #1 — Wire the model registry (role → tier → model), behaviour-neutral

**Problem.** `config/models.py` has zero callers. Four agents hardcode `claude-sonnet-4-5` across three
different construction idioms. Model choice can't change without editing agent code — and three dead IDs
sat there for months precisely because nothing called them.

**Target state.** Two-level registry. Agents ask by **role**; roles map to **tiers**; tiers pin **model
IDs**. Adding a tier or swapping a model is a change **in `config/models.py` and nowhere else**.

Storage is a **Python literal, not YAML** — deliberate divergence from `PromptLoader`. Reasons: C8 forbids
`prompts/`; a repo-root YAML would need the `parents[3]` trick, which already only works from a source
checkout (`prompts/` isn't shipped in the wheel); mypy checks a dict but not `yaml.safe_load` → `Any`; and
the drift guard still works (roles ⊆ agent files) against a literal. Revisit if pins must change without a
deploy.

```python
PROVIDER = "anthropic"

class ModelError(Exception): ...

@dataclass(frozen=True, slots=True)
class Tier:
    id: str
    accepts_temperature: bool      # sonnet-5 / opus-4-8 → 400 if temperature sent at all

@dataclass(frozen=True, slots=True)
class Role:
    tier: str
    temperature: float | None = None   # a REQUEST, honoured only if the tier accepts one

@dataclass(frozen=True, slots=True)
class ModelSpec:
    role: str; tier: str; id: str
    temperature: float | None
    temperature_dropped: bool
    @property
    def qualified_id(self) -> str:            # "anthropic:claude-sonnet-4-5"
        return f"{PROVIDER}:{self.id}"
    def chat_kwargs(self) -> dict[str, Any]:  # temperature ABSENT (not None) when dropped
        kwargs = {"model": self.id}
        if self.temperature is not None:      # `is not None` — 0.0 is falsy!
            kwargs["temperature"] = self.temperature
        return kwargs

_TIERS = {
    "cheap":    Tier(id="claude-haiku-4-5",  accepts_temperature=True),
    "balanced": Tier(id="claude-sonnet-4-5", accepts_temperature=True),   # ← what agents run TODAY
    "deep":     Tier(id="claude-opus-4-8",   accepts_temperature=False),
}
_ROLES = {
    "kpi":        Role(tier="balanced", temperature=0.0),
    "synthesis":  Role(tier="balanced", temperature=0.2),
    "delivery":   Role(tier="balanced", temperature=0.0),
    "evaluation": Role(tier="balanced"),   # create_llm_as_judge takes no temperature
}

class ModelRegistry:
    def __init__(self, tiers=None, roles=None) -> None: ...
    def resolve(self, role: str) -> ModelSpec: ...   # raises ModelError; instance dict cache
    def roles(self) -> list[str]: ...
    def tiers(self) -> list[str]: ...

model_registry = ModelRegistry()
```

`ModelRegistry.get()` is **deleted** (zero callers; its silent default-to-`balanced` is the exact failure
mode that hid the mis-pin). Unknown role/tier now **raises `ModelError`**, mirroring `PromptError`.

**Files affected**
- `src/agentic_app/config/models.py` — rewrite per above.
- `agents/kpi_agent.py:18` — `ChatAnthropic(**model_registry.resolve("kpi").chat_kwargs())`
- `agents/synthesis_agent.py:18`, `agents/delivery_agent.py:29` — same pattern.
- `agents/evaluation_agent.py:19` — `model=model_registry.resolve("evaluation").qualified_id`
- **Drop `# type: ignore[call-arg]`** from the three `ChatAnthropic` sites — `**kwargs` hides the keys from
  mypy, so the ignore becomes an `unused-ignore` **error** under strict. Verify with `make lint`, not by eye.
- `tests/unit/test_model_registry.py` — new.
- **Do NOT touch** `tests/integration/test_trajectory.py:212` (5th hardcoded site). It's `skipif`-gated,
  never runs in CI, and wiring it would add a first-party import to the hermetic module.
- **Do NOT add** FinBERT (`sentiment_agent.py:47`) — local HuggingFace pipeline, no tier/temperature/prefix.

**Acceptance criteria**
- [ ] `resolve("kpi").chat_kwargs() == {"model": "claude-sonnet-4-5", "temperature": 0.0}`
- [ ] `resolve("evaluation").qualified_id == "anthropic:claude-sonnet-4-5"` (byte-identical to today)
- [ ] `"temperature" not in ModelRegistry(roles={"r": Role(tier="deep", temperature=0.0)}).resolve("r").chat_kwargs()`
- [ ] `resolve("nope")` raises `ModelError` listing valid roles
- [ ] Guard: `set(model_registry.roles()) <= {p.stem.removesuffix("_agent") for p in agents.glob("*_agent.py")}`
      — **subset, not equality**: `ingestion`/`sentiment` have no Anthropic model
- [ ] Guard: no role has `temperature_dropped is True`
- [ ] `test_trajectory.py` and `test_prompt_registry.py` pass **unmodified** (proves C1/C8 held)
- [ ] `make lint && make test` green; **`make eval` unchanged**

**Related:** blocks #10. Depends on ADR-0009.
**⚠️ PR note:** this re-pins `balanced` from `claude-sonnet-5` → `claude-sonnet-4-5`. That is **not** a
revert of `4bd5d07` — every ID it chose is valid. It decouples *wire the registry* from *change which model
runs*. Say so, or a reviewer reads it as a regression.

---

### Issue #2 — Extract `checkpoint.py` from `main.py`; fix the orphaned connection

**Problem.** `main.py:41-96` mixes CLI, env reading, backend selection, fallback, graph construction, and
result printing in one 96-line function. It is untestable without a database. It also has a latent bug: if
`PostgresStore` succeeds but `PostgresSaver` throws, the store is rebound to `InMemoryStore` while the
Postgres one **stays registered in the ExitStack** — a live connection, unused, for the whole run.

**Target state.** `src/agentic_app/orchestration/checkpoint.py` owns selection, construction, lifetime and
**durability reporting** of both backends. It reads no environment and imports no settings (C2) — `db_url`
is a parameter. That's what makes it testable.

```python
@contextmanager
def open_persistence(
    db_url: str, *, sqlite_path: str = "earningsedge.db", report: Callable[[str], None] = print,
) -> Iterator[tuple[BaseCheckpointSaver[Any], BaseStore]]:
    """Open checkpointer + store for one run. Both stay open for the `with` body."""
```

`report` is **injected** (main passes `typer.echo`; tests pass `list.append`) so the module has no CLI
dependency. Postgres imports stay **function-local** — pointless on the SQLite path, and late binding is
what lets tests monkeypatch without a database.

**The orphan fix** — ownership becomes transactional:
```python
with ExitStack() as attempt:
    store = attempt.enter_context(PostgresStore.from_conn_string(db_url))
    checkpointer = attempt.enter_context(PostgresSaver.from_conn_string(db_url))
    store.setup(); checkpointer.setup()
    stack.push(attempt.pop_all())   # both up → transfer ownership. push, not enter_context.
```
On any failure `attempt.__exit__` closes what it opened; nothing leaks into the outer stack.

Also: the fallback message gains `{exc}`, not just `type(exc).__name__` — today a permissions error and a
connection refusal are indistinguishable and both say "start it with docker compose".

**`main.py` after extraction** — `run()` goes **96 → 30 lines**:
```python
db_url = os.environ.get("DATABASE_URL", "")
with open_persistence(db_url, report=typer.echo) as (checkpointer, store):
    graph = build_graph(checkpointer=checkpointer, store=store)
    ...  # everything from build_graph down UNCHANGED and still inside the `with` (C3)
```
Removed: `ExitStack` import, `typing.Any`, both branches, and the redundant inner `load_dotenv()`
(`main.py:22` already calls it at module import, and it doesn't override set vars — **call this out in
review**, don't sneak it in).

**Files affected**
- `src/agentic_app/orchestration/checkpoint.py` — new. **No new `__init__.py`**; `orchestration/__init__.py`
  exists and must **stay inert** — a re-export would drag `checkpoint.py` into the hermetic test's import
  graph (C1-adjacent).
- `src/agentic_app/main.py` — collapse `run()`.
- `tests/unit/test_checkpoint.py` — new.

**Acceptance criteria**
- [ ] `graph.invoke` still lexically inside the `with` (C3) — savers outlive the invoke
- [ ] **Regression test:** store opens, saver raises → store is **closed before the body runs**
      (`assert closed == ["store"]` *inside* the body). This test **fails against today's `main.py`**.
- [ ] Unreachable Postgres → falls back to SQLite, message contains the exception text
- [ ] A raise in the body still closes both backends
- [ ] `graph.py` untouched; `test_trajectory.py` passes unmodified
- [ ] `BaseCheckpointSaver[Any]` parameterised (it's generic; `disallow_any_generics` is on)
- [ ] `make lint && make test` green

**Related:** blocks #3. Depends on ADR-0006.

---

### Issue #3 — Swap `InMemoryStore` → `SqliteStore`; fixes bug B-1

**Problem.** On the default config `sentiment_surprise` is **permanently 0.0** and `n_quarters` is 0. The
0.20-weighted tone term of the signal is always zero and `confidence` is capped — **the scores are wrong,
not merely unavailable**. `delivery_agent` writes tone to the store every run; the write is discarded at
exit, so history can never accumulate.

**Target state.** `langgraph.store.sqlite.SqliteStore` is **already installed** (ships with
`langgraph-checkpoint-sqlite`, an existing declared dependency). `_open_sqlite` becomes:
```python
store = stack.enter_context(SqliteStore.from_conn_string(sqlite_path))
store.setup()
```
The non-durable warning from #2 is then **deleted, not tuned** — there is nothing left to warn about.

**Files affected:** `orchestration/checkpoint.py` (`_open_sqlite` only — #2 isolated it deliberately),
`tests/unit/test_checkpoint.py`, `examples/AAPL-Q1-FY2025-brief.md` (regenerate; it currently documents
the bug).

**Acceptance criteria**
- [ ] Two consecutive local runs for the same ticker: the 2nd sees `n_quarters >= 1`
- [ ] `sentiment_surprise` non-zero once ≥2 quarters exist
- [ ] Decide + document: SQLite file locking when `SqliteSaver` and `SqliteStore` share a path
- [ ] Eval baseline re-recorded — **this changes signal scores**

**Related:** depends on #2. **Blocks #11** (evals must baseline *after* this).
**⚠️** This is a behaviour change. Land it alone, not folded into #2.

---

### Issue #4 — Fix the live "escalate to the Critic" prompt (bug B-2)

**Problem.** `prompts/shared/tool_use_policy.md:11-14` is rendered into the **running** delivery prompt.
It instructs the agent to "use exponential backoff" (no facility exists) and "escalate to the **Critic**"
(no such role — deleted in `94ede9c`). This is the only *user-visible* fossil.

**Target state.** `prompts/shared/tool_use_policy.md` edited; `prompts/delivery/v2.md` created;
`prompts/registry.yaml` bumped `delivery.active_version: v2`. **v1.md is never edited** (immutability).

**Note:** this is the **first real exercise of `docs/runbooks/rollback-a-prompt.md`** — a good forcing
function to fix that runbook (#12) at the same time.

**Acceptance criteria**
- [ ] No "Critic" in any rendered prompt: `grep -ri critic prompts/` clean
- [ ] `test_prompt_registry.py` + `test_prompt_loader.py` pass (v2 has an H1 naming its role)
- [ ] `v1.md` byte-identical to before

---

### Issue #5 — Delete the scaffold packages

**Problem.** Six modules with zero importers, describing an app that was never built.

**Target state.** Deleted, each with an ADR recording *why*:

| Delete | ADR | Rationale |
|---|---|---|
| `src/agentic_app/mcp/` | 0011 | Zero intent, zero consumer |
| `src/agentic_app/memory/` | 0005 | Superseded by `BaseStore` — already shipped |
| `src/agentic_app/rag/` + `scripts/seed_vectorstore.py` | 0007 | 0/13 skills need retrieval |
| `src/agentic_app/tools/` (`registry.py`, `schemas.py`) | 0008 | Empty registry; 0 tools; real tools come from Composio |
| `src/agentic_app/api/app.py` | 0008 | `/health` only; never served (`Dockerfile` CMD is the CLI) |
| `src/agentic_app/llm/anthropic_client.py` | 0009 | Stub, 0 callers |
| `src/agentic_app/agents/base.py` | 0008 | `BaseAgent`, 0 subclasses |

Also: `docker-compose.yml` `vectordb` service; `pgvector` + `sentence-transformers` deps;
`.env.example` RAG block; `tests/unit/test_tools/` (an `assert True` placeholder).

**⚠️ Sequencing trap:** `agents/base.py` — do **not** rename it to `base_agent.py`; `test_prompt_registry`
globs `*_agent.py` and would demand a `prompts/base/` dir (C8). Deleting it is safe.

**Acceptance criteria**
- [ ] `make lint && make test` green after deletion (proves they were dead)
- [ ] Import-graph audit shows no new orphans
- [ ] Each deletion cites its ADR in the commit message

---

### Issue #6 — `config/settings.py`: wire it or delete it

**Problem.** `Settings` requires `anthropic_api_key`, `database_url`, `vectordb_url` and instantiates **at
import** — so importing it raises `ValidationError` unless all three are set. It has zero importers, which
is the only reason the test suite passes. It also demands `vectordb_url` for a subsystem #5 deletes, and
uses the deprecated pydantic-v1 `class Config`.

**Target state — decide explicitly:**
- **(a) Delete it.** Env reading already lives at 3 call sites (`main.py`, `ingestion_agent`,
  `delivery_agent`) and works.
- **(b) Wire it properly** — drop `vectordb_url`, move to `SettingsConfigDict`, make instantiation lazy
  (`@lru_cache` factory, not module-level), then route the 3 call sites through it.

**(b) is the better end state** (typed config is why the module exists) but **must not** be reachable from
`graph.py` at import (C2). Lazy instantiation is the mechanism.

**Acceptance criteria**
- [ ] `test_trajectory.py` passes with **no** env vars set
- [ ] `vectordb_url` gone (after #5)
- [ ] If (b): no module-level `Settings()` call anywhere

---

### Issue #7 — `observability/tracing.py`: OTel bootstrap + `@traced`

**Problem.** `opentelemetry-api`, `-sdk`, `-exporter-otlp` and `langsmith` are all **declared and never
imported**. `docker-compose` runs an otel-collector (4317/4318/8888) and Prometheus (9090);
`otel-collector-config.yaml` and `prometheus.yml` both exist; `make trace` exports
`OTEL_EXPORTER_OTLP_ENDPOINT`. **The entire pipeline is provisioned with zero producers** —
`OTEL_EXPORTER_OTLP_ENDPOINT` is completely inert.

**Nuance the docs get right:** LangSmith tracing **already works** without this module —
`LANGSMITH_TRACING=true` is read by the LangGraph SDK itself. That's why `architecture.md` says
*"partial"*. Only the OTel leg is missing.

**Target state.** `observability/tracing.py` exposing the API the docs already name
(`AGENTS.md:294-296`): a **`@traced` decorator** + an `init_tracing()` OTel bootstrap, env-gated on
`OTEL_ENABLED` / `OTEL_EXPORTER_OTLP_ENDPOINT`, **no-op when unset**.

**⚠️ C1:** `@traced` must **not** be applied in `graph.py`. Decorate inside agent modules (faked away by
the trajectory test) or wrap at the `checkpoint`/`main` boundary.

**Acceptance criteria**
- [ ] `make trace` produces spans in collector stdout
- [ ] Unset env → zero overhead, no import of OTel SDK
- [ ] `test_trajectory.py` passes unmodified
- [ ] `otel-collector-config.yaml`: `logging` exporter is **deprecated** → `debug`; note traces currently
      go nowhere but stdout (no Jaeger/Tempo backend)

---

### Issue #8 — `llm/retry.py`: circuit breaker only

**Problem.** Spec (3 docs + the recovered `api_integration` skill) conflates **two** retry problems:

| | LLM rate limits | Data-provider rate limits |
|---|---|---|
| Call site | `ChatAnthropic` ×4 | `yfinance` in `kpi_agent._consensus`; `earningscall`/`edgar` in `ingestion_agent` |
| Belongs in | `llm/retry.py` | **not `llm/`** — a shared HTTP helper |

**And the Anthropic SDK already ships `max_retries` with exponential backoff.** So the honest scope is
narrow: the **circuit breaker** ("fast-fail after N failures") and, separately, third-party retry.

**Target state.** `llm/retry.py` = circuit breaker only, applied at the registry seam (#1). Third-party
retry is a **separate issue** — `tenacity` and `stamina` are both installed (transitively; declare one).

**⚠️** `llm/` is vestigial: `anthropic_client.py` has 0 callers (#5 deletes it). Decide `llm/`'s fate in
ADR-0009 before adding to it — the registry, retry, and `@traced` all want the **same seam**.

---

### Issue #9 — Prometheus metrics + fix the broken scrape

**Problem.** `prometheus.yml` targets `localhost:8888` — inside the Prometheus container `localhost` is
*itself*, not the collector. **The scrape is broken even before any producer exists.** Must be
`otel-collector:8888`. Also `prometheus-client` is **not a dependency** despite the container, the config,
and the forwarded port.

**⚠️ Sequencing:** the 4 intended counters are *tokens, latency, tool calls, eval scores*.
**Two are unmeasurable today** — zero tools are registered (#5 deletes the registry) and `run.py` emits
`None`. Land **after** #11.

---

### Issue #10 — Model upgrade: `balanced` → `claude-sonnet-5`, drop temperature

**Problem.** Agents run `claude-sonnet-4-5`, two generations behind.

**Target state.** With #1 landed, a **two-line registry edit**:
```python
"balanced": Tier(id="claude-sonnet-5", accepts_temperature=False),   # ← 1
"kpi": Role(tier="balanced"),                                        # ← 2 (drop temperature)
```
`test_chat_kwargs_match_the_pre_registry_call_sites` **goes red** — forcing conscious acceptance that
kpi/delivery lose `temperature=0` determinism and synthesis loses `0.2`. **That red test is the point.**

**⚠️** This is a real behaviour change: `temperature=0` was presumably chosen for deterministic KPI
extraction. Needs an eval baseline (#11) to measure.

**Acceptance criteria**
- [ ] No `temperature` sent to Sonnet 5 (would 400)
- [ ] Eval baseline recorded **before** and compared **after**
- [ ] Golden test updated deliberately, with the rationale in the PR

---

### Issue #11 — Evals: flip `PLACEHOLDER = False`

**Problem.** `evals/run.py` has `PLACEHOLDER = True` and always exits 0. **The `eval-gate` job runs on
every PR and is decorative** — it goes green on any PR, including one that genuinely regresses quality.
ADR-0004 **pre-authorises** the flip. Also: `evals/suites/regression.yaml` binds to `agent: researcher`
and `agent: supervisor` (don't exist); `datasets/researcher_qa.jsonl` is a fossil;
`evals/scorers/llm_judge.py` **contains no LLM judge**; `scripts/check_eval_regression.py` is real but
never invoked.

**Target state.** Real datasets keyed `{ticker, year, quarter}`; a real `llm_judge`; wire
`check_eval_regression.py`; flip the flag.

**Acceptance criteria**
- [ ] A deliberately regressed prompt **fails** the gate (prove it isn't decorative)
- [ ] `researcher_qa.jsonl` deleted; `regression.yaml` binds to real agents

---

### Issue #12 — Sweep the remaining fossils

`5ed85a8` swept the agent-facing docs and stopped. Not yet swept:

- **`docs/runbooks/agent-stuck-in-loop.md`** — nearly every instruction is impossible.
  `scripts/replay_trace.py` is a `print()`. `AGENT_MAX_STEPS`/`step_count`/`scratchpad` don't exist. The SQL
  has **five errors in four lines** (wrong table, wrong column, and PostgreSQL doesn't support
  `UPDATE … LIMIT`). Line 58 says "Supervisor checks routing".
- **`docs/runbooks/rollback-a-prompt.md`** — `researcher/v2.md` throughout; every role is at v1; "check eval
  scores in registry" is impossible (all `eval_score: 0.0`).
- **`skills/README.md`** — documents a 5-skill set that no longer exists.
- **`.github/prompts/new-agent.prompt.md`** — `src/orchestration/router.py`, "the supervisor router logic".
- **`.github/instructions/`** — `test_researcher_agent_e2e`, `tools.web_search`, "let the Critic decide",
  "prefer async" (nodes are sync).
- **`docs/prompt-templates/`** — referenced 4× as a mandated workflow step; **never existed**.
- **`.vscode/mcp.json`** — 3 servers, none installed.
- **`.claude/commands/eval.md`** — `/eval researcher_qa`.

---

### Issue #13 — Add the drift guards that would have caught all of this

**Problem.** Nothing caught 8 dead modules, 3 rotted model IDs, or docs describing a different app.
`test_prompt_registry.py` exists **only because someone got burned and wrote a test** — it's the sole drift
class that can't silently rot.

**Target state — three guards, ordered by value:**
1. **Docs-path test** (hermetic, fast) — assert every `src/...` path cited in `CLAUDE.md` / `AGENTS.md` /
   `copilot-instructions.md` exists. Would have failed the day `checkpoints.py` was mentioned.
2. **Dead-module check** in pre-commit — `vulture`, or the import-graph script from this session. **Ruff
   does not catch an unimported module.**
3. **Scheduled model-ID liveness check** — `GET /v1/models` per pinned ID, nightly. Needs network → can't
   live in `make test`.

---

### Issue #14 — Unit-test the agents; add a coverage floor (bug B-3) ⚠️ HIGHEST VALUE

**Problem.** **All six agents are at 0% coverage** — 215 untested statements. Verified:

| Module | Stmts | Missed | Cov |
|---|---|---|---|
| `ingestion_agent.py` | 47 | 47 | **0%** |
| `kpi_agent.py` | 46 | 46 | **0%** |
| `sentiment_agent.py` | 41 | 41 | **0%** |
| `delivery_agent.py` | 37 | 37 | **0%** |
| `synthesis_agent.py` | 25 | 25 | **0%** |
| `evaluation_agent.py` | 19 | 19 | **0%** |

`test_trajectory.py` **fakes every agent away** — it proves the graph *wiring* and nothing about the logic.
`addopts` measures coverage but there is **no `--cov-fail-under`** and no `[tool.coverage]` section, so 32%
never fails. The domain logic this repo exists for — `signal-synthesis-scoring`'s weights, `_z` clamp,
`100*tanh(raw)`, `_pct` surprise math, `_ratios` hedging, `guidance_direction` thresholds — is **entirely
unverified**.

**Why this is the plan's biggest hazard.** Phase 1 claims to be "behaviour-neutral", gated on `make eval`
being unchanged. But `make eval` is a **placeholder that always passes** (B-4). So today there is **no net
beneath the refactor at all**. This issue builds it.

**Target state.** Unit tests for the pure functions — no network, no API key, no LLM. They're already pure:
```python
def test_z_clamps_to_the_documented_range():        # synthesis_agent._z  → [-3, 3]
def test_score_is_100_tanh_of_the_weighted_sum():   # weights 0.35/0.20/0.20/0.10/0.15
def test_direction_thresholds():                    # >10 bullish, <-10 bearish, else neutral
def test_pct_guards_zero_and_none_consensus():      # kpi_agent._pct
def test_guidance_direction_thresholds():           # >1 raise, <-1 cut, else maintain
def test_ratios_are_per_1000_tokens():              # sentiment_agent._ratios
def test_route_after_eval_thresholds():             # 0.8 / 2 — currently duplicated in the fake!
```
Then set `--cov-fail-under` at the achieved number to ratchet.

**⚠️ Two traps this surfaces:**
1. `test_trajectory.py:120-122`'s fake `route_after_eval` **duplicates the real thresholds** (`< 0.8`, `< 2`)
   rather than importing them. A real unit test on the true function makes that duplication visible.
2. `evaluation_agent.py:56-57`'s commented-out block says `GROUNDING_THRESHOLD = 0.7` while the live code
   uses `0.8`. **Do not resurrect constants from the comment** — test the live behaviour.

**Acceptance criteria**
- [ ] Each of the 6 agents has unit tests for its pure functions; no network, no key
- [ ] `--cov-fail-under=<achieved>` in `addopts`; CI fails if coverage drops
- [ ] `test_trajectory.py` still passes unmodified
- [ ] Land **before Phase 1** if possible — it's the net for "behaviour-neutral"

**Related:** de-risks #1, #2, #3, #10.

---

### Issue #15 — Repair the agent-facing command/scaffold files ⚠️ ACTIVELY HARMFUL

**Problem.** These files are **executed by AI agents**, so their drift causes wrong code to be written —
unlike prose drift, which merely misleads.

| File | Damage |
|---|---|
| `.claude/commands/new-agent.md:10` | `src/agents/{role}_agent.py` — wrong path, **and** "with `BaseAgent` inheritance" — a class **this plan deletes** (#5) |
| `.claude/commands/new-agent.md:13` | `src/orchestration/router.py` — **has never existed** |
| `.claude/commands/new-agent.md:27` | repeats the wrong path |
| `.github/prompts/new-agent.prompt.md:77,117` | same `router.py` fossil, "the supervisor router logic" |
| `.claude/commands/eval.md:10,20` | `/eval researcher_qa`, "Researcher agent only" |
| `.vscode/mcp.json` | uses key **`mcpServers`**; VS Code expects **`servers`** — *and* all 3 servers (`github`/`postgres`/`playwright`) are absent from `uv.lock`, so every `uv run` fails |
| `evals/README.md:56-58` | "**Regression gate**: Fails PR if score < baseline" — **it cannot** (`PLACEHOLDER = True`) |

**⚠️ Sequencing:** `new-agent.md` must be fixed **in the same PR as #5** (which deletes `base.py`), or the
command tells agents to inherit from a deleted class. Also note C8: a new `*_agent.py` requires a matching
`prompts/<role>/` dir **and** a `registry.yaml` entry, or `test_prompt_registry.py` fails. The command
doesn't say so — that's why it should generate all three.

**Acceptance criteria**
- [ ] Every path in `.claude/commands/` and `.github/prompts/` resolves on disk
- [ ] `new-agent.md` reflects the real contract: `{role}_node(state) -> dict`, a `graph.py` node + edges,
      a `prompts/<role>/v1.md`, and a `registry.yaml` entry (all three, per C8)
- [ ] `.vscode/mcp.json` — fix the key **or delete the file** (ADR-0011 deletes `mcp/`; deleting is honest)
- [ ] `evals/README.md` no longer claims a gate that doesn't exist
- [ ] Covered by #13's docs-path guard so it can't rot again

---

### Issue #16 — Restore enforced review on prompt changes (bug B-4)

**Problem.** Three no-ops compound into zero governance: `evals/run.py` `PLACEHOLDER = True` → always
exit 0; `prompt-diff.yml` → `exit 0  # Let eval gate decide pass/fail`; `CODEOWNERS` → `@owner` /
`@ai-eng-team` are **placeholders**, and GitHub silently ignores rules naming non-existent teams.
**A prompt can regress agent quality and reach `main` with no gate.** `CLAUDE.md:138` claims otherwise.

**Target state.** Pick the mechanism and make exactly one real:
- **CODEOWNERS** → real users/teams, **plus branch protection requiring owner review** (CODEOWNERS alone
  enforces nothing without it).
- **`prompt-diff.yml`** → either make it a real gate or delete it (it currently only echoes).
- **`eval-gate`** → made real by #11.

Also fix the `prompts/` over-match (it catches `src/agentic_app/prompts/loader.py` too — probably
unintended), and correct `CLAUDE.md:138` if the claim stays false.

**Acceptance criteria**
- [ ] A PR touching `prompts/` **requires** a named human reviewer, verified on a test PR
- [ ] No placeholder handles remain in `CODEOWNERS`
- [ ] `CLAUDE.md:138`'s claim is either true or removed

**Related:** #11 (real eval gate), #12.

---

### Issue #17 — CI / release / packaging hygiene

**Problem.** Verified defects, none blocking today but each a latent trap:

| # | Defect | Consequence |
|---|---|---|
| 1 | `release.yml:33` `tag_name: ${{ github.ref }}` + `on.push.branches:[main]` | On a **branch** push, `github.ref` = `refs/heads/main` → creates a release named after a branch |
| 2 | `release.yml:29` `actions/create-release@v1` | **Archived/deprecated** |
| 3 | `release.yml:28` `git describe --tags --abbrev=0` | **Hard-fails** with no tags in the repo |
| 4 | `@pytest.mark.langsmith` (`test_trajectory.py:197`) | **Unregistered** — no `markers` in `[tool.pytest.ini_options]` → `PytestUnknownMarkWarning` |
| 5 | `agentevals` (`test_trajectory.py:205`) | Used via `importorskip`, **undeclared** — degrades silently, so the LLM-judge test may *never* run and nobody notices |
| 6 | `pyproject.toml:76` + `:90` | Dev deps duplicated across `[project.optional-dependencies]` **and** `[dependency-groups]` — **already drifted** (`types-pyyaml` only in the group) |
| 7 | `ci.yml:37-39` postgres service | Started for the `test` job but **no `DATABASE_URL` is exported** → tests never reach it. Pure cost. |
| 8 | `docker-compose.yml:1` `version: '3.9'` | Obsolete in Compose v2 |
| 9 | compose `app` mounts `.:/workspace`, Dockerfile `WORKDIR /app` | Mount is **inert** |
| 10 | compose `app` exposes `:8000` | Nothing listens — `CMD` is a one-shot CLI |
| 11 | `otel-collector-config.yaml` `logging` exporter | **Deprecated** → `debug`; image is `:latest` so it may already warn |

**Acceptance criteria**
- [ ] `release.yml` gated on tags only, or `tag_name` derived correctly; `create-release@v1` replaced;
      `git describe` tolerates no-tags
- [ ] `markers = ["langsmith: ..."]` registered; `agentevals` declared in the dev group (or the test deleted)
- [ ] Dev deps declared **once** — pick `[dependency-groups]` (uv installs it by default) and drop the extra
- [ ] CI postgres service either **used** (export `DATABASE_URL`) or **removed**
- [ ] Compose: drop `version:`, fix or drop the volume + port

---

### Issue #18 — Uniform error-as-state across all six agents (+ fix the ingestion silent-swallow)

**Problem.** Error handling is applied inconsistently. `EarningsState.errors` is
`Annotated[list[str], operator.add]` ([state.py:53](../src/agentic_app/orchestration/state.py#L53)),
so the framework is *ready* to accumulate failures across parallel branches — but only two of six
agents use it, and one of those has a silent-swallow bug:

| Agent | `try/except`? | Writes `errors[]`? | On failure it… |
|---|---|---|---|
| ingestion | ✅ | ✅ (partial) | logs — **but the earningscall branch silently swallows**, see below |
| kpi | ✅ | ✅ | logs, continues (returns `kpis: [{}]`) |
| sentiment | ❌ | ❌ | **throws → aborts the run** |
| synthesis | ❌ | ❌ | **throws → aborts the run** |
| evaluation | ❌ | ❌ | **throws → aborts the run** |
| delivery | ✅ | ❌ (logs to `delivery_log`) | logs, continues |

Two consequences:

1. **A failure in the fan-out is only survivable on the KPI side.** If the sentiment branch throws
   (FinBERT is local and low-risk, but its `store.search` hits Postgres and *can* fail), the whole
   parallel superstep aborts — discarding the sibling branch's completed work. Same for
   synthesis/evaluation downstream.
2. **The ingestion silent-swallow** at
   [ingestion_agent.py:54-55](../src/agentic_app/agents/ingestion_agent.py#L54-L55):
   ```python
   except Exception as e:
       return_err = f"earningscall: {e}"  # noqa: F841   <- assigned, never used → never reaches errors[]
   ```
   The primary-source (earningscall) failure is written to a dead local and discarded; the `# noqa`
   suppresses the linter warning that would flag it. A run can silently fall back to the SEC-EDGAR
   path — or produce a hollow brief — with **no error recorded anywhere**.

**Target state.** A single, deliberate error-handling contract, applied uniformly:

- Every node wraps its risky work (LLM calls, external APIs, store I/O) and, on failure, **appends to
  `state["errors"]` instead of raising** — leaning on the existing `operator.add` reducer, which
  already merges concurrent writes from parallel branches correctly.
- **Decide the fatal-vs-degradable boundary per node** — this is a design step, not a blanket
  catch-all. Some failures *should* stop the run: if ingestion retrieves **no** transcript from
  *either* source, a downstream "brief" is hollow and arguably worse than an explicit failure. The
  issue must state, per agent, what degrades (log + continue with a hole) vs what is terminal.
- Fix the ingestion silent-swallow: the earningscall failure must reach `errors[]`, and the `# noqa:
  F841` goes away.
- `main.py` currently never prints `state["errors"]` — surface it in the CLI output so a
  degraded-but-completed run is visibly degraded, not silently wrong.

**Files affected:** all six `agents/*_agent.py` (add/normalize handling), `main.py` (print `errors`),
`tests/unit/test_agents/*` (the characterization tests from #14 pin *current* behaviour — several
will change intentionally and must be updated, not force-passed).

**Acceptance criteria**
- [ ] Every agent's external/LLM/store call path either records to `errors[]` or is a **documented,
      deliberate** terminal failure
- [ ] The ingestion earningscall failure reaches `errors[]`; no `# noqa: F841` remains
- [ ] A forced sentiment-branch failure produces a completed run with the error logged (today it
      aborts) — proven by a test
- [ ] Parallel-branch errors from both fan-out agents both appear in the merged `errors[]` (reducer
      behaviour, proven by a test)
- [ ] `main.py` prints `errors` on completion
- [ ] `#14`'s characterization tests updated deliberately, with the behaviour change noted in the PR

**Related / sequencing:** Phase 2 (FIX) — it is a **behaviour change** (a previously-aborting run now
completes with a logged error), so it depends on the #14 test net being in place (done) and touches
the same agent files as #1 (model registry); land it **after** #1 to avoid churn in those files.
Surfacing `errors` in the CLI overlaps with the observability work (#7) — keep them separate.

---

## DELIVERABLE 3 — ADRs + task checklist

> House style: `docs/adr/0004` — name the drift, the failure mode, the rejected alternatives, and the exact
> flag to flip later. Only 1 of 4 existing ADRs matches reality; **six of the seven topics have no ADR at all.**

### ADR-0005 — Long-term memory via LangGraph BaseStore

**Status:** Accepted · **Supersedes:** the deleted `skills/memory_management/SKILL.md`

**Context.** `memory/` is labelled "planned" in three docs. It is not planned — it is **done differently**.
`94ede9c` deleted `memory_management` and in the same commit wired `BaseStore` end-to-end: `main.py` selects
it, `graph.py` injects it, `sentiment_agent.py:83` reads it, `delivery_agent.py:74` writes it. The deleted
skill's short-term half (windowed history, token-budgeted compaction) is **moot**: `EarningsState` has no
`messages` key, nodes are single-shot, there are no turns.

**Decision.** Long-term memory = LangGraph `BaseStore`, namespace `("sentiment_history", ticker)`, key
`f"{year}Q{quarter}"`. Short-term memory: **N/A** for a stateless pipeline. **Delete `src/agentic_app/memory/`.**

**Consequences.** The "planned" label is retired. **The Store is only durable on Postgres** → forces ADR-0006.
The namespace/key format is duplicated across `delivery_agent`, `sentiment_agent`, and `test_trajectory` —
three places, no shared constant. Accepted for now; noted.

---

### ADR-0006 — Persistence: durable store by default (amends ADR-0001)

**Status:** Accepted · **Amends:** ADR-0001

**Context.** ADR-0001 records "**PostgreSQL checkpoints for persistence**" as *the* decision. The code makes
Postgres **opt-in and secondary**: `main.py` defaults to SQLite and *silently downgrades* on any failure.
This is an **unrecorded decision reversal**, and it has a live consequence: the SQLite path gives
`InMemoryStore`, so `sentiment_surprise` is permanently 0.0 (bug B-1). `examples/AAPL-Q1-FY2025-brief.md`
is the receipt: "n_quarters = 0".

**Decision.**
1. Ratify SQLite-by-default for local dev — the fallback is *good* ergonomics.
2. **But the store leg must be durable too.** `langgraph.store.sqlite.SqliteStore` is already installed →
   use it. `InMemoryStore` is retained **only** for tests.
3. Extract selection into `orchestration/checkpoint.py`; fix the orphaned-connection bug.

**Rejected.** *Postgres-required* (kills zero-infra local dev). *Warn-only* (leaves a known-wrong-numbers bug
shipping, at zero saving — `SqliteStore` costs no new dependency).

**Consequences.** Local runs accumulate real sentiment history → **signal scores change**; eval baselines
must be re-recorded. SQLite file-locking between `SqliteSaver` and `SqliteStore` needs a decision.

---

### ADR-0007 — RAG is not required; delete `rag/`

**Status:** Accepted

**Context.** `architecture.md:52-53` specs "ingest → chunk → embed → hybrid retrieve + rerank behind a
pgvector/Qdrant Protocol", and `.env.example` pre-chose the hyperparameters (all-MiniLM-L6-v2, chunk 512/50,
top-k 5, cross-encoder rerank). But: **0 of 13 domain skills reference retrieval.** Ingestion fetches whole
transcripts by `(ticker, year, quarter)`; `kpi_agent` passes `text[:18000]` to Claude; `evaluation_agent`
passes `[:12000]`. A single earnings call fits in context. The one genuine cross-quarter need — trailing
8-quarter tone — is served by the **Store**, not a vectorstore.

The artifacts also **actively conflict**: the running service is **Qdrant** (`docker-compose`,
`VECTORDB_URL=:6333`, devcontainer port), the declared Python dependency is **pgvector**, and
**`qdrant-client` is absent from `uv.lock` entirely**. Neither path works as-is. *The vectorstore decision
was never made* — so there is no decision to preserve.

**Decision.** **Delete** `rag/`, `scripts/seed_vectorstore.py`, the `vectordb` compose service, the
`pgvector` + `sentence-transformers` deps, the `.env.example` RAG block, and `vectordb_url` from `Settings`.
**Revisit when** multi-quarter or cross-company semantic search becomes a requirement — at which point
**pgvector is the likely choice** (reuses the Postgres already running for checkpoints; zero new infra).

**Consequences.** Frees a required-but-unread `Settings` field (a real bug). Drops ~1GB of transitive deps
(torch, transformers) — **but** `sentiment_agent` needs `transformers` for FinBERT, so verify the dep graph
before removing `sentence-transformers`. ADR-0001's "mitigated via adapters" no longer needs a Protocol here.

---

### ADR-0008 — Supersede ADR-0002 (tools/skills boundary)

**Status:** Accepted · **Supersedes:** ADR-0002

**Context.** ADR-0002 is almost entirely fiction. All six named examples (`web_search`, `code_exec`,
`file_io`, `web_research`, `code_execution`) are deleted Layer-1 artifacts. **Zero tools exist** —
`tools/registry.py` is a `ToolRegistry` with an empty dict and nothing registered; the "Anthropic schema"
export it promises doesn't exist. **No agent loads any skill at runtime** — nothing reads `SKILL.md`. It also
cites `src/tools/`, the wrong path — the exact drift class ADR-0004 blames for breaking `eval.yml`.

**Decision.** Record the *de facto* boundary:
- **Skills** = design documents for humans and coding agents, hand-implemented into agent modules. **Not**
  runtime-loaded. (13 skills; every one is faithfully implemented — this is the repo's *strength*.)
- **Tools** = supplied by **Composio**, bound dynamically in `delivery_agent.py:54`. There is no in-repo tool
  registry. **Delete `tools/`**, `api/app.py`, `agents/base.py`.

**Consequences.** "tool calls" becomes unmeasurable as a metric → constrains ADR-0010. Blocks any MCP design
(ADR-0011) — you cannot design tool integration before deciding whether tools exist.

---

### ADR-0009 — One seam for model routing, retry, and tracing

**Status:** Accepted

**Context.** Three needs converge on the same place: model routing (`config/models.py`, 0 callers),
retry/circuit-breaker (`llm/retry.py`, missing), and `@traced` (named, never written). Meanwhile `llm/` is
vestigial — `anthropic_client.py` has 0 callers and agents construct `ChatAnthropic` inline. Adding `retry.py`
beside a dead client is building on sand.

**Decision.**
1. **`config/models.py` is the seam.** Role → tier → model; `resolve(role) -> ModelSpec`.
2. **Storage: Python literal, not YAML.** C8 forbids `prompts/`; a root YAML would replicate `PromptLoader`'s
   `parents[3]` bug (`prompts/` isn't in the wheel); mypy checks a dict but not `yaml.safe_load`; and the
   drift guard (roles ⊆ agent files) works either way. **No guard is lost.**
3. **Unknown role raises `ModelError`.** The old silent default-to-`balanced` is *exactly* the failure mode
   that hid three dead IDs.
4. **`temperature` is per-role, reconciled against per-tier `accepts_temperature`** — Sonnet 5 / Opus 4.8
   reject it with a 400. Reconciliation makes the eventual upgrade a **registry-only edit**.
5. **Delete `llm/anthropic_client.py`.** `llm/retry.py` = **circuit breaker only**; the SDK's `max_retries`
   covers backoff. **Third-party retry** (yfinance 429, SEC 10 req/s) is a *different problem* at a
   *different call site* and does **not** belong in `llm/`.

**Rejected.** *Bare `str` return* — can't carry temperature + prefix. *Pydantic* — validates untrusted
boundary input; this is trusted in-process data (frozen dataclass is right). *Prefix as role data* — every
tier is Anthropic by construction; it's a rendering, not config.

**Consequences.** Wiring is behaviour-neutral **only because** `balanced` is pinned to `claude-sonnet-4-5`.
FinBERT stays out (local pipeline; no tier/temperature/prefix semantics).

---

### ADR-0010 — Observability: `@traced` + OTel init + 4 counters

**Status:** Accepted

**Context.** The most precisely specced stub. `AGENTS.md:294-296` names the missing API — "**no `@traced`
decorator**". `AGENTS.md:320` names the metrics — "Prometheus counters for **tokens, latency, tool calls,
eval scores**". All four OTel/LangSmith deps are declared and **none is imported**. A three-service pipeline
(otel-collector → prometheus → port-forward) is fully provisioned with **zero producers**.

**Decision.** `observability/tracing.py` = OTel bootstrap + `@traced`, env-gated, **no-op when unset**.
`observability/metrics.py` = Prometheus counters — **deferred**: 2 of 4 metrics are unmeasurable (ADR-0008
deletes the tool registry; `run.py` emits `None` scores). Sequence after ADR-0008 and the eval work.

**Consequences.** Requires `prometheus-client` (**new dep**) + a `mypy` override (`ignore_missing_imports =
false` globally). `prometheus.yml` scrape target is **broken** (`localhost:8888` inside the Prometheus
container) and must be fixed regardless. `otel-collector-config.yaml`'s `logging` exporter is deprecated →
`debug`. **`@traced` must not touch `graph.py`** (C1). LangSmith already works — only the OTel leg is missing.

---

### ADR-0011 — MCP deferred; delete `mcp/`

**Status:** Accepted

**Context.** The weakest intent in the repo. No ADR, skill, prompt, README mention, or consumer. Two
irreconcilable readings (app *consumes* MCP vs app *exposes* MCP) and **no evidence for either**.
`.vscode/mcp.json` names `github`/`postgres`/`playwright` servers — **none is installed**; every `uv run`
would fail. It's dev-harness config, not architecture. The `edgartools-mcp` binary is an accident of a
dependency chosen for ingestion.

**Decision.** **Delete `src/agentic_app/mcp/`.** Record that no consumer was identified. Revisit only with a
concrete requirement. **Must follow ADR-0008** — you cannot design MCP tool integration before deciding
whether tools exist at all.

---

### Task checklist

```text
PHASE 0 · RECORD
  [ ] ADR-0005 memory = BaseStore
  [ ] ADR-0006 persistence (amends 0001)
  [ ] ADR-0007 RAG not required
  [ ] ADR-0008 supersede ADR-0002
  [ ] ADR-0009 llm/ seam
  [ ] ADR-0010 observability
  [ ] ADR-0011 MCP deferred
  [ ] Mark ADR-0002 "Superseded by 0008"; ADR-0001 "Amended by 0006"

PHASE 0.5 · BUILD THE NET  ⚠️ do first
  [ ] #14 unit tests for the 6 agents' pure functions (B-3)
  [ ] #14 --cov-fail-under=<achieved> in addopts

PHASE 1 · SEAMS (behaviour-neutral — eval MUST NOT move)
  [ ] #1  model registry + wire 4 sites        [ ] tests/unit/test_model_registry.py
  [ ] #2  checkpoint.py + orphan fix           [ ] tests/unit/test_checkpoint.py

PHASE 2 · FIX
  [ ] #3  SqliteStore swap (B-1)               [ ] regenerate examples/ brief
  [ ] #4  tool_use_policy v2 (B-2)             [ ] registry bump
  [ ] #18 uniform error-as-state + fix ingestion silent-swallow (← #14, after #1)

PHASE 3 · DELETE
  [ ] #5  mcp/ memory/ rag/ tools/ api/ base.py anthropic_client.py
  [ ] #15 .claude/commands/new-agent.md  ← SAME PR as #5 (it cites BaseAgent)
  [ ] #6  settings.py wire-or-delete

PHASE 4 · BUILD
  [ ] #7  observability/tracing.py
  [ ] #8  llm/retry.py (circuit breaker only)
  [ ] #9  prometheus.yml fix + metrics.py

PHASE 5 · RAISE
  [ ] #11 evals PLACEHOLDER=False   ← do BEFORE #10
  [ ] #10 model upgrade + drop temperature

PHASE 6 · SWEEP
  [ ] #12 runbooks · skills/README · .github/instructions · evals fossils
  [ ] #15 .claude/commands/eval.md · .github/prompts · .vscode/mcp.json · evals/README
  [ ] #16 governance: CODEOWNERS real handles + branch protection (B-4)
  [ ] #17 release.yml · pytest markers · agentevals · pyproject dedup · CI postgres · compose
  [ ] #13 drift guards (docs-path test · dead-module check · model liveness)
```

---

## DELIVERABLE 4 — Narrative design document

### Where we are

`earnings-edge` is a **fixed LangGraph pipeline**, not a supervisor topology:

```text
ingest → {sentiment, kpi} → synthesize → evaluate → (revise ⟲ | deliver) → END
```

Seven nodes, one conditional edge (`route_after_eval`), a revision budget of 2, and a grounding threshold of
0.8. The domain layer is **good**: all 13 skills are faithfully implemented — `signal-synthesis-scoring`'s
weights match `synthesis_agent.py` digit-for-digit. **The problem was never the pipeline. It's the scaffold
around it.**

### Where we're going

**Every module has a caller.** Today 8 of 18 don't. After Phase 3, the package is the pipeline plus three
supporting seams (`config/models.py`, `orchestration/checkpoint.py`, `observability/tracing.py`).

**One seam for cross-cutting LLM concerns.** Model choice, retry, and tracing all want the same chokepoint.
`config/models.py` becomes it: agents ask by *role*, roles map to *tiers*, tiers pin *models*. An agent no
longer knows which model it runs — it knows what kind of work it does.

**Config that is wired or gone.** `settings.py` currently crashes on import and has zero importers. Either it
becomes the real config path or it goes. No third state.

**Durability that matches the promise.** ADR-0001 said Postgres; the code silently downgraded. That gap made
`sentiment_surprise` permanently 0.0. `SqliteStore` closes it at zero dependency cost.

**Drift guarded by tests, not vigilance.** `test_prompt_registry.py` is the only drift class that can't rot,
because someone wrote a test. Phase 6 extends that to docs paths, dead modules, and model IDs.

### The three ideas that make it work

**1. Two-level indirection.** One level (tier → model) means every agent hardcodes *which tier*. Two levels
(role → tier → model) means re-tiering one agent is a registry edit. The `temperature` reconciliation lives at
the tier boundary — which is what turns the Sonnet 5 upgrade into a two-line change with a test that goes red
to make you think.

**2. Ownership is transactional.** `open_persistence` yields from inside its `ExitStack`, so backends live
exactly as long as the caller's `with` body — preserving C3. The `pop_all()` handoff means a half-failed
Postgres attempt closes what it opened instead of orphaning a connection.

**3. Delete beats build.** Three of five stubs get deleted with an ADR explaining why. The plan's largest
contribution isn't the code it adds — it's the code and documentation it removes. A deleted module can't drift.

### What we're deliberately NOT doing

- **Not building RAG.** 0/13 skills need it. Deferred with a written trigger.
- **Not building MCP.** No consumer. Deferred.
- **Not rebuilding memory.** It shipped as `BaseStore`.
- **Not upgrading the model during the refactor.** Phase 1 must be provably mechanical.
- **Not touching `graph.py`'s imports.** C1 is load-bearing.

### Migration checklist (solo execution order)

```text
□  1. Read this doc + the 8 hard constraints. C1/C2/C3 are the ones that bite.
□  2. Branch off main. Confirm `main` == `origin/main` first.
□  3. Write the 7 ADRs (Phase 0). Cheap, unblocks everything, no code risk.
      Use docs/adr/0004 as the template — it's the only one that matches reality.
□ 3b. Issue #14 — UNIT-TEST THE AGENTS FIRST. All six are at 0%; make eval is a
      no-op. Until this lands, "behaviour-neutral" in step 4 is unverifiable.
      ✅ gate: --cov-fail-under set; 6 agents' pure functions covered
□  4. Issue #1 — model registry. TRUE no-op: `balanced` = claude-sonnet-4-5.
      ✅ gate: make lint && make test && make eval  →  eval UNCHANGED
      ✅ gate: test_trajectory.py + test_prompt_registry.py pass UNMODIFIED
□  5. Issue #2 — checkpoint.py. Write the orphan regression test FIRST; it must
      fail against today's main.py, then pass.
      ✅ gate: graph.invoke still inside the `with`
□  6. Issue #3 — SqliteStore. FIRST behaviour change. Re-record eval baseline.
      ✅ gate: 2 consecutive runs → n_quarters >= 1
□  7. Issue #4 — tool_use_policy v2. First real use of the rollback runbook.
□  8. Issue #5 + #15's new-agent.md — delete the scaffold. SAME PR: the command
      cites BaseAgent, which #5 deletes. Wide diff, low risk. One ADR ref per commit.
      ✅ gate: green suite AFTER deletion proves they were dead
□  9. Issue #6 — settings.py: wire or delete. No third state.
□ 10. Issue #11 — evals real. MUST precede #10 (you need a baseline).
      ✅ gate: a deliberately regressed prompt FAILS the gate
□ 11. Issue #16 — governance. Only meaningful once #11 makes the gate real.
      ✅ gate: a test PR touching prompts/ REQUIRES a named reviewer
□ 12. Issue #10 — model upgrade. Golden test goes red; accept it deliberately.
□ 13. Issue #7 — @traced + OTel. ⚠️ never in graph.py.
□ 14. Issue #8 — circuit breaker only. Third-party retry is a separate issue.
□ 15. Issue #9 — fix prometheus.yml scrape (localhost→otel-collector), then metrics.
□ 16. Issue #12 + rest of #15 — sweep runbooks/instructions/commands/evals fossils.
□ 17. Issue #17 — CI/release/packaging hygiene. Low risk, do it while waiting on evals.
□ 18. Issue #13 — drift guards. Do this or you'll be back here in six months.
```

---

## Verification

**Per-issue gate (every issue):**
```bash
make lint          # ruff + mypy --strict on src
make test          # 27 passed, 1 skipped today — must not regress
uv run pre-commit run --files <changed>   # incl. gitleaks + prompt-consistency
```

**Phase 0.5 gate — build the net (#14):**
```bash
uv run pytest tests/ --cov=src/agentic_app --cov-report=term | grep agent
# TODAY: all six agents 0%. After #14 they must be non-zero and --cov-fail-under set.
```

**Phase 1 gate — the "provably mechanical" proof:**
```bash
make eval          # MUST be identical to pre-refactor
uv run pytest tests/integration/test_trajectory.py tests/unit/test_prompt_registry.py
# ^ both must pass UNMODIFIED — that's the evidence C1 and C8 held
```
⚠️ **`make eval` is a placeholder that always exits 0** until #11. Until then it proves nothing —
#14's agent unit tests are the real net. Do not treat a green `make eval` as evidence.

**End-to-end (drive the real pipeline, don't just run tests):**
```bash
docker compose up -d postgres
DATABASE_URL=postgresql://agentic:dev-password@localhost:5432/earnings_edge \
  uv run python -m agentic_app.main run --ticker AAPL --year 2025 --quarter 1
# expect: "[checkpoint] durable Postgres backend"; GROUNDING/SIGNAL/DELIVERY printed
```

**Bug B-1 fixed (#3):** run the same ticker twice locally with no `DATABASE_URL`; the second run must show
`n_quarters >= 1`. Today it is always 0.

**Registry behaviour-neutrality (#1):**
```bash
uv run python -c "from agentic_app.config.models import model_registry as r; \
  print(r.resolve('kpi').chat_kwargs(), r.resolve('evaluation').qualified_id)"
# {'model': 'claude-sonnet-4-5', 'temperature': 0.0} anthropic:claude-sonnet-4-5
```

**Model IDs are live (#10):** verify against `GET /v1/models` before pinning. The Python SDK needs
`truststore.inject_into_ssl()` on this machine (the house pattern — see `scripts/check_anthropic_key.py`);
`uv` needs `UV_SYSTEM_CERTS=1`.

**Tracing (#7):** `make trace` → spans in `docker compose logs otel-collector`. Unset env → zero overhead.
