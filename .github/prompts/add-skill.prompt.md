---
name: /add-skill
description: "Create a new agent runtime skill (multi-step workflow with bundled assets)"
---

# /add-skill

Scaffolds a new runtime skill (multi-step workflow with instructions + optional resources):

1. Create `skills/{skill_domain}/SKILL.md` with progressive disclosure
2. Create `skills/{skill_domain}/scripts/` directory (optional)
3. Create `skills/{skill_domain}/resources/` directory (optional)
4. Add to `skills/README.md` registry

**Usage**: `@claude /add-skill rag_retrieval` → scaffolds RAG retrieval skill

**Auto-generates**:
- SKILL.md with "When to use", workflow, tools, output format, pitfalls
- scripts/ and resources/ directories (optional)
- Entry in skills/README.md

**Example skill structure**:
```
skills/web_research/
├── SKILL.md
├── scripts/
│   └── parse_earnings_call.py
└── resources/
    └── sec_filing_fields.md
```
