# ADR-0002: Tools vs. Skills Boundary

**Status**: **Superseded by ADR-0008**
**Date**: 2026-02-05

> **Superseded (2026-07-15).** Every load-bearing claim below is now false: all six named examples
> (`web_search`, `code_exec`, `file_io`, `web_research`, `code_execution`) are deleted scaffold
> artifacts; **zero tools exist**; **no agent loads a skill at runtime**; and `src/tools/` is the
> wrong path (the package is `src/agentic_app/tools/`).
>
> See **ADR-0008**: skills are **design documents**, tools come from **Composio**.
> Retained for history — do not implement against this.

## Context

We need to clarify the boundary between atomic tools and multi-step skills.

## Decision

- **Tools**: Atomic callables with Anthropic schema (web_search, code_exec, file_io)
- **Skills**: Multi-step workflows with bundled instructions (web_research, code_execution)

Tools are:
- Called by agents directly
- Single responsibility
- Defined in `src/tools/`

Skills are:
- Loaded by agents at runtime
- Orchestrate multiple tools
- Bundled with instructions in `skills/`

## Rationale

- Clear separation of concerns
- Skills encapsulate complex workflows
- Tools remain simple and reusable
- Agents can compose skills ad-hoc

## Consequences

- Agents must know which skill to load (requires reasoning or config)
- Skill instructions must be clear and discoverable
