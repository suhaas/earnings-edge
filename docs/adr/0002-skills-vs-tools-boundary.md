# ADR-0002: Tools vs. Skills Boundary

**Status**: Accepted
**Date**: 2026-02-05

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
