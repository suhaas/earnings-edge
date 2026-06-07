---
name: kpi-extraction
description: Extracts structured financial KPIs (revenue, EPS, segment revenue, guidance) from earnings text using few-shot Claude structured output. Use whenever numeric KPIs and forward guidance must be pulled from a transcript or press release into a typed schema.
---

# KPI Extraction (few-shot LLM structured extraction)

## Purpose
Turn unstructured earnings text into a validated EarningsKPIs Pydantic object.

## Inputs
- `prepared_remarks: str`, `press_release_text: str`

## Outputs (EarningsKPIs schema)
- revenue_actual: float|None, eps_actual: float|None
- revenue_guidance_next_q: float|None, eps_guidance_next_q: float|None
- guidance_language: str, segment_revenue: dict[str,float]

## Tools used
- ChatAnthropic(model="claude-sonnet-4-5").with_structured_output(EarningsKPIs,
  method="json_schema").

## Agent responsible
KPI Delta Extractor.

## Procedure
1. Build a system prompt with 1-2 few-shot examples of text -> EarningsKPIs JSON.
2. Invoke structured model on (press_release_text + prepared_remarks).
3. Validate; null out fields not explicitly stated (no hallucinated numbers).

## Edge cases / notes
- Numbers are often "$X.X billion" — instruct the model to normalize to a numeric unit.
- Never invent guidance; if absent set fields None and guidance_language="not provided".
- Prefer press_release_text for headline numbers (cleaner than spoken remarks).