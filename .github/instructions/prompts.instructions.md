---
name: prompts-instructions
applyTo: ["prompts/**/*.md", "docs/prompt-templates/**/*.md"]
description: "Rules for system prompts: immutable versioning, composition, guardrails. Use when: drafting or updating prompts, promoting v1→v2, updating registry.yaml."
---

# Prompt Development Guidelines

## Versioning (CRITICAL)

- **Immutable once shipped**: Never edit `prompts/{role}/v1.md` if it's in production
- **Bump version**: Create `v2.md`, `v3.md`, etc.; old versions stay for rollback
- **Registry**: Update `prompts/registry.yaml` to activate the new version
  ```yaml
  roles:
    researcher:
      active_version: v2
      versions:
        v1:
          date: "2026-01-15"
          eval_score: 0.82
          author: "alice"
        v2:
          date: "2026-02-01"
          eval_score: 0.89
          author: "bob"
  ```

## Development Workflow

1. **Draft**: Experiment in `docs/prompt-templates/{role}-draft.md` (no versioning)
2. **Test locally**: Run agent with draft prompt; validate against eval suite
3. **Version**: Move to `prompts/{role}/vN.md` (immutable)
4. **Activate**: Update `prompts/registry.yaml` with new active version
5. **Push**: Triggers `prompt-diff.yml` CI gate → eval comparison → human review

## Composition

- **Shared fragments**: Include `prompts/shared/safety.md`, `output_formats.md`, `tool_use_policy.md`
- **Loading**: `src/prompts/loader.py` composes fragments at runtime
- **Example structure**:
  ```markdown
  # Researcher Agent Prompt v2
  
  {{shared.safety}}
  
  ## Role
  You are the Research Agent...
  
  {{shared.tool_use_policy}}
  
  ## Output Format
  {{shared.output_formats.json}}
  ```

## Guardrails

- **Safety**: Include guardrails from `prompts/shared/safety.md` in every agent prompt
- **Tool use**: Reference `prompts/shared/tool_use_policy.md` for error handling + recovery
- **Output**: Align with contracts in `prompts/shared/output_formats.md`

## Eval & Iteration

- **Eval suite**: `evals/suites/regression.yaml` defines the baseline
- **Regression gate**: If new version scores < baseline, PR fails (requires justification or prompt fix)
- **Metadata**: Track author + eval score in registry so you know which version won

## Anti-patterns

- **Editing shipped versions**: NEVER change v1.md if it's in production
- **Vague descriptions**: Every prompt change should have clear rationale in PR description
- **No eval before merge**: Prompt changes must run the `ci.yml` eval-gate CI gate
