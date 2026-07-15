# ADR-0008: Skills Are Design Docs; Tools Come From Composio

**Status**: Accepted
**Date**: 2026-07-15
**Supersedes**: ADR-0002

## Context

ADR-0002 defined a tools/skills boundary. Every load-bearing claim in it is now false.

**Its six named examples are all deleted scaffold artifacts.** `web_research` and `code_execution`
were deleted in `94ede9c`; `web_search`, `code_exec`, and `file_io` never existed.

**"Tools ... Defined in `src/tools/`" — zero tools exist.** `src/agentic_app/tools/` contains
`registry.py` (a `ToolRegistry` whose `self.tools` dict is never written) and `schemas.py` (which,
despite its docstring promising "Tool input/output Pydantic schemas", contains only a `ToolError`
class). `@tool_registry.register` appears **nowhere**. `ToolError` has zero importers. The
"Anthropic schema" export ADR-0002 and `AGENTS.md:230` promise does not exist. The path is also
wrong — the package is `src/agentic_app/tools/`, the same drift class ADR-0004 blames for breaking
`eval.yml`.

**"Skills: Loaded by agents at runtime" — nothing reads `SKILL.md`.** The 13 skills are referenced
only in *code comments*. They were hand-implemented into the agent modules by humans and coding
agents. "Agents can compose skills ad-hoc" never happened.

What is actually true is better than what the ADR claimed. The 13 skills are **closely
implemented**: `consensus-estimate-retrieval`'s yfinance fallback is implemented verbatim, and
`grounding-faithfulness-eval`'s "threshold 0.8, max 2 revisions" matches `route_after_eval` exactly.
The skills are a good, largely accurate design corpus. They are just not a *runtime* mechanism.

**But "largely" is doing real work in that sentence, and it is the strongest argument for this ADR.**
`signal-synthesis-scoring`'s five *weights* match `synthesis_agent.py` digit-for-digit — and two of
its *transforms* do not:

| | Skill (`SKILL.md:26`) | Code (`synthesis_agent.py:32-33`) |
|---|---|---|
| sentiment | `0.20*sentiment_surprise` | `0.20 * sentiment_surprise * 3` — undocumented 3× amplification |
| certainty | `0.10*net_certainty_qa` | `0.10 * _z(net_certainty_qa, 5)` — skill says raw |

Likewise `hedging-certainty-features` asks for ratios computed **separately** for prepared remarks
vs Q&A ("Q&A hedging spikes are the signal"); the code computes Q&A only.

Because the skills are *documents*, nothing detected any of this — a skill cannot fail a test.
Both drifts are now pinned by named guards in `tests/unit/test_agents/`, which is the only mechanism
that can. This is precisely why the boundary needs recording: skills are **specs**, and specs need
**tests** to stay true, not good intentions.

And real tools do exist — they come from **Composio**, bound dynamically in `delivery_agent.py:54`
(`session.tools()` → LangChain `StructuredTool`s → `create_agent`). They never touch `tools/`.

## Decision

Record the **de facto** boundary:

- **Skills** (`skills/`) are **design documents** for humans and coding agents: the specification a
  developer implements against, and the context an AI agent reads before editing an agent module.
  They are **not** loaded at runtime. Each has a stable shape (Purpose / Inputs / Outputs / Tools
  used / Agent responsible / Procedure / Edge cases) and names the node it governs.
- **Tools** are supplied by **Composio** at runtime and bound to the delivery agent. There is no
  in-repo tool registry and no in-repo tool schema layer.

**Delete** `src/agentic_app/tools/` (`registry.py`, `schemas.py`), `src/agentic_app/api/app.py`, and
`src/agentic_app/agents/base.py` — all zero-caller scaffold. `tests/unit/test_tools/` (an
`assert True` placeholder) goes with them.

`api/app.py` is included because it is the same class of artifact: a `GET /health`-only FastAPI app
that is never served. `Dockerfile`'s `CMD` runs the Typer CLI; the uvicorn line is a **comment**.
The real entrypoint is `python -m agentic_app.main run`.

`agents/base.py`'s `BaseAgent` has **zero subclasses** — every node is a plain function, which is
what LangGraph wants.

## Rationale

- **The ADR was describing a different application.** Superseding is cheaper and more honest than
  amending claim-by-claim.
- **Skills-as-docs is a real, working pattern** — and demonstrably a good one, given how faithfully
  the 13 are implemented. Naming it lets us keep it deliberately instead of apologising for it.
- **Deleting an empty registry removes a trap.** A `ToolRegistry` with a `register` decorator invites
  someone to register a tool into a structure nothing reads.
- **Composio is the tool layer.** Two competing tool concepts is one too many.

## Alternatives Considered

- **Build the tool registry as ADR-0002 specifies**: rejected — nothing would call it. The only tools
  the domain needs are Composio's delivery tools, which arrive fully formed.
- **Make skills runtime-loadable** (parse `SKILL.md`, inject into prompts): rejected — no requirement
  asks for it, and the prompts already carry role instructions via `PromptLoader`. It would duplicate
  the prompt layer.
- **Amend ADR-0002 in place**: rejected — the house style (ADR-0004) supersedes rather than rewrites,
  and every substantive claim would change.
- **Keep `api/app.py` for a future service**: rejected — it is 14 lines that will be rewritten
  whenever a real API is wanted; `Dockerfile`'s comment records the intent adequately.

## Consequences

- **"Tool calls" becomes permanently unmeasurable** as a metric. ADR-0010 names it as one of four
  intended Prometheus counters; with no in-repo tool layer, only Composio could report it. ADR-0010
  must account for this.
- **Blocks any MCP design** (ADR-0011): you cannot design tool integration before deciding whether an
  in-repo tool layer exists. It now explicitly does not.
- `.claude/commands/new-agent.md` instructs agents to use "`BaseAgent` inheritance" — it **must** be
  fixed in the same change that deletes `base.py`, or it will actively instruct agents to inherit
  from a deleted class.
- `AGENTS.md`'s "Tools & Skills Boundary" section and `skills/README.md`'s dead 5-skill table must be
  rewritten to match.
- If a real in-repo tool layer is ever needed, this ADR is superseded — and the design should start
  from the requirement, not from ADR-0002's `web_search`/`code_exec` examples.
