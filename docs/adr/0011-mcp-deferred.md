# ADR-0011: MCP Deferred — No Consumer Identified; Delete `mcp/`

**Status**: Accepted
**Date**: 2026-07-15
**Depends on**: ADR-0008

## Context

`src/agentic_app/mcp/` is a stub whose `__init__.py` docstring reads
`"""Model Context Protocol integration."""`. That sentence is the **entire** design corpus.

Searched exhaustively. There is **no ADR, no skill, no prompt, no README section, and no consumer**.
The only statements anywhere are existence-denials — `AGENTS.md:54-55` and `CLAUDE.md:47-48` both say
only that the package is a stub. **All 13 domain skills reference MCP zero times.**

The two circumstantial signals are thin and both partly broken:

- **`.vscode/mcp.json`** declares three servers — `github`, `postgres`, `playwright` — each as
  `"command": "uv", "args": ["run", "<name>-mcp-server"]`. **None of the three is in `uv.lock`**, so
  every one fails to start. It also uses the key **`mcpServers`**, whereas VS Code's `.vscode/mcp.json`
  expects **`servers`**. And it is *dev-harness* config — it wires the **editor** to MCP servers, not
  the application. It is aspirational scaffold, not architecture.
- **`.venv/Scripts/edgartools-mcp.exe` exists.** It is the only MCP artifact that resolves — and it is
  a console script that ships with `edgartools`, a dependency chosen for `ingestion_agent`. It is an
  **accident of a dependency picked for a different reason**. `AGENTS.md`'s claim that "the venv does
  ship `edgartools-mcp`" is literally true and carries no intent.

**Two irreconcilable readings, and nothing disambiguates them:**

1. **The app consumes MCP** — `mcp/` holds a client mounting external MCP servers as agent tools. The
   `edgartools-mcp` coincidence faintly hints at this: it could replace `ingestion_agent`'s direct
   `from edgar import Company, set_identity` with an MCP tool call.
2. **The app exposes MCP** — `mcp/` serves earnings-edge itself as an MCP server. Also plausible:
   `api/app.py` is `GET /health` only and the real entrypoint is a CLI, so there is no HTTP surface
   an MCP server would compete with.

There is **no evidence for either**. Reading (1) has a faint edge; that is not enough to design on.

## Decision

**Delete `src/agentic_app/mcp/`.** Record that **no consumer was identified** and that neither
reading could be substantiated.

**Revisit only with a concrete requirement** — e.g. "expose the earnings pipeline to Claude Desktop"
(reading 2), or "replace direct `edgartools` calls with a maintained MCP server" (reading 1). The
successor ADR should derive its design from that requirement, not from this stub's docstring.

**Also fix or delete `.vscode/mcp.json`.** Given this ADR, **deleting it is the honest option**: it
names three servers that cannot start, under a key VS Code does not read. If it is kept, both the key
(`mcpServers` → `servers`) and the missing dependencies must be fixed — otherwise it is a third piece
of MCP fiction.

## Rationale

- **You cannot design tool integration before deciding whether tools exist.** ADR-0008 has now
  decided: there is **no in-repo tool layer**; tools come from Composio. An MCP client's whole purpose
  would be to *supply tools* — into a layer that no longer exists. That ordering is why this ADR
  depends on ADR-0008 and why MCP is the lowest-priority stub.
- **Zero intent is a finding, not a gap.** Every other stub in this repo has *some* spec. This one has
  a docstring. Inventing a design would be fabricating intent — the exact failure this refactor is
  correcting.
- **The strongest "evidence" is a coincidence.** Treating `edgartools-mcp`'s presence as a design
  signal would be reading tea leaves from a transitive console script.

## Alternatives Considered

- **Build an MCP client** (reading 1): rejected — no consumer, and ADR-0008 removed the tool layer it
  would feed. Also duplicates working direct SDK calls in `ingestion_agent` for no stated benefit.
- **Build an MCP server** (reading 2): rejected — no requirement, no user. The CLI is the entrypoint
  and nobody has asked to drive it from an MCP host.
- **Keep the stub, mark it deferred**: rejected — a deferred stub is indistinguishable from an
  unfinished one, which is exactly how `mcp/` has been read as "planned" in three docs for months.
- **Adopt `edgartools-mcp` because it happens to be installed**: rejected — availability is not a
  requirement. `ingestion_agent`'s direct edgar calls work and are covered by
  `skills/sec-edgar-8k-retrieval`.

## Consequences

- `src/agentic_app/mcp/` is deleted; the "planned" list in `AGENTS.md`, `CLAUDE.md`, and
  `.github/copilot-instructions.md` loses another entry.
- `AGENTS.md:54-55`'s note about `edgartools-mcp` should go with it — true, but it implies an
  intent that does not exist.
- **No dependency change.** No MCP library was ever declared, so nothing to remove.
- If MCP is later wanted, this ADR is superseded. The successor must state which of the two readings
  it implements and why — that ambiguity is the reason this one exists.
