---
name: /review-pr
description: "Staff-engineer code review: security, regressions, prompt diffs"
---

# /review-pr

Performs an expert code review pass on the current branch:

- **Security**: Checks for secrets, unsafe code patterns, privilege escalation
- **Performance**: Identifies bottlenecks (N+1 queries, unbounded loops, token waste)
- **Regressions**: Runs eval suite and flags score drops
- **Prompt changes**: Diffs versioned prompts, checks registry consistency

**Usage**: `@claude /review-pr` → generates staff-engineer review

**Checklist included**:
- ✓ Lint + type-check pass (make lint)
- ✓ Tests pass (make test)
- ✓ Evals pass (make eval)
- ✓ Secrets not committed
- ✓ Prompt versions immutable (v1.md unchanged if shipped)
- ✓ PR description includes eval delta

**Output**: Markdown review with action items + approval/request-changes decision.
