---
name: analyst-brief-generation
description: Generates a concise Markdown analyst brief from the synthesized signal and supporting evidence. Use whenever a human-readable earnings brief must be produced for delivery to Slack/Notion/email.
---

# Analyst-Brief Markdown Generation

## Purpose
Render a one-page Markdown brief: headline signal, beats/misses, tone, guidance, risks.

## Inputs
- signal (SurpriseSignal), kpis, sentiment features, ticker/quarter

## Outputs
- brief_markdown: str  (every numeric claim must be traceable to inputs)

## Tools used
- ChatAnthropic(model="claude-sonnet-4-5") with a strict template + the structured inputs.

## Agent responsible
Signal Synthesis & Report agent.

## Procedure
1. Provide the model ONLY the structured inputs (not raw transcript) to limit hallucination.
2. Enforce sections: TL;DR signal, Beat/Miss table, Tone & Hedging, Guidance, Risks, Sources.
3. Require inline attribution like "(EPS $X vs consensus $Y, +Z%)".

## Edge cases / notes
- Keep numbers ONLY from state inputs; the grounding agent will reject invented figures.
- Cap length (~400 words) for Slack readability.