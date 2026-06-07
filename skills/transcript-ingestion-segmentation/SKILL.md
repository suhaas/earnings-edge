---
name: transcript-ingestion-segmentation
description: Ingests an earnings-call transcript and segments it into prepared remarks vs analyst Q&A. Use whenever sentiment, tone, or KPI analysis needs the call split into the two sections, or when a raw transcript must be normalized before downstream agents run.
---

# Transcript Ingestion & Prepared-Remarks-vs-Q&A Segmentation

## Purpose
Produce two clean text blocks — prepared remarks and Q&A — from the best available source.

## Inputs
- `ticker: str`, `year: int`, `quarter: int`

## Outputs
- `transcript_prepared: str`
- `transcript_qa: str`
- `transcript_source: str`  # "earningscall" | "edgar_8k" | "regex_split"

## Tools used
- earningscall: `get_company(ticker).get_transcript(year, quarter, level=4)`
  -> `.prepared_remarks`, `.questions_and_answers`, `.text`.
- Fallback: sec-edgar-8k-retrieval skill + regex Q&A boundary splitter.

## Agent responsible
Transcript Ingestion agent.

## Procedure
1. Try earningscall level=4 (gives `.prepared_remarks` + `.questions_and_answers` directly).
2. If unavailable (non-AAPL/MSFT on free tier, or None), get full transcript text
   (`level=1`) or the 8-K press release; then regex-split on the Q&A boundary:
   pattern `(?i)(question[- ]and[- ]answer|we (will|'ll) now (begin|take).*questions|
   operator.*(first|next) question|\[?\s*Q\s*&\s*A\s*\]?)`.
3. Everything before the first match = prepared remarks; after = Q&A.

## Edge cases / notes
- earningscall free tier is limited to AAPL and MSFT — always implement the EDGAR fallback.
- If no Q&A boundary is found, set `transcript_qa = ""` and flag it in `errors`.
- Strip operator boilerplate and forward-looking-statement disclaimers before scoring.