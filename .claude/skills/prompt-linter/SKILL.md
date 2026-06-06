---
name: prompt-linter
description: "Checks new prompt versions for unsafe patterns, format drift, registry consistency"
---

# Prompt Linter Skill

Validates prompt files during development to prevent shipping bad prompts.

## Checks

- **Immutability**: v1.md, v2.md, etc. cannot be edited if shipped (checked via registry date)
- **Composition**: All {{shared.*}} fragments must exist
- **Guardrails**: safety.md and tool_use_policy.md included
- **YAML syntax**: registry.yaml is valid, role name matches version directory
- **Output formats**: Align with shared/output_formats.md contracts
- **Forbidden patterns**: No hardcoded secrets, no raw eval(), no unsafe tool instructions

## Invoked by

- Pre-commit hook (before commit)
- CI lint gate (before push)
- `/review-pr` command (manual)

## Example Output

```
✓ prompts/researcher/v2.md: valid format, all fragments found
✗ prompts/analyst/v1.md: IMMUTABLE VIOLATION — this version is in prod (registry.yaml dated 2026-01-15)
  → Create v2.md instead
✗ prompts/shared/safety.md: {{shared.MISSING}} — fragment not found
  → Check spelling in composition
```
