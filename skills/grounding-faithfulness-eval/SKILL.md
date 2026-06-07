---
name: grounding-faithfulness-eval
description: Verifies that every claim in the analyst brief is supported by the source transcript and structured KPIs using an LLM-as-judge, returning a faithfulness score. Use whenever a generated brief must be checked for hallucination before delivery.
---

# Grounding / Faithfulness Evaluation (the eval agent)

## Purpose
Score brief faithfulness in [0,1]; trigger self-correction if below threshold.

## Inputs
- brief_markdown, transcript_prepared+qa, kpis (as reference context)

## Outputs
- grounding_score: float, grounding_comment: str

## Tools used
- openevals: `create_llm_as_judge(prompt=HALLUCINATION_PROMPT, model="anthropic:claude-sonnet-4-5",
  feedback_key="faithfulness")` -> returns {"score": bool|float, "comment": str}.

## Agent responsible
Evaluation / Grounding agent.

## Procedure
1. Pass inputs=transcript/kpis context, outputs=brief_markdown.
2. The judge flags unsupported numbers/claims; map its boolean/score to [0,1].
3. Write grounding_score + comment to state.

## Edge cases / notes
- HALLUCINATION_PROMPT scores higher = more grounded (less hallucination).
- Determinism: set judge temperature 0; log to LangSmith for audit.
- Threshold 0.8 with max 2 revisions prevents infinite loops.