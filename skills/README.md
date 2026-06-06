# Agent Skills

This directory contains runtime skills that agents can load and use dynamically.

## What is a Skill?

A **Skill** is a reusable, multi-step workflow bundled with instructions and optional assets (scripts, resources).

Skills are:
- **Invoked on-demand** by agents at runtime
- **Self-contained**: Include everything needed (instructions, examples, tools)
- **Progressive disclosure**: Start simple, layer in complexity
- **Versioned**: Immutable once shipped

## Skill Directory

| Skill | Purpose |
|-------|---------|
| `web_research/` | Multi-step web research workflow |
| `code_execution/` | Sandboxed code execution with limits |
| `file_io/` | Safe, scoped file operations |
| `api_integration/` | Resilient API calls with retries |
| `memory_management/` | Persistent memory for agents |

## How Agents Use Skills

1. Agent recognizes it needs a capability (e.g., "I need to research earnings")
2. Agent loads the skill instructions (SKILL.md)
3. Agent follows the workflow and uses available tools
4. Agent returns structured output per skill's output contract

## Creating a New Skill

Use `/add-skill` in Claude Code to scaffold:
```
skills/{skill_domain}/
├── SKILL.md              # Instructions, workflow, tools, output format
├── scripts/              # Optional helper scripts
└── resources/            # Optional reference material
```

Each skill must include:
- **SKILL.md**: When to use, workflow steps, tools, output format, examples, pitfalls
- **Tools**: Reference to available tools (defined in src/tools/)
- **Output format**: Clear contract for skill outputs

## Examples

See individual SKILL.md files for detailed instructions.
