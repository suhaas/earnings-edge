---
name: hedging-certainty-features
description: Extracts linguistic hedging and certainty features (uncertainty words, modal verbs, certainty markers) from earnings text. Use whenever management's confidence level or evasiveness must be quantified alongside FinBERT sentiment.
---

# Hedging & Certainty Linguistic Feature Extraction

## Purpose
Quantify managerial confidence/evasiveness via wordlist ratios per 1,000 words.

## Inputs
- `text: str`

## Outputs
- `hedge_ratio: float`       # hedging words per 1k words
- `certainty_ratio: float`   # certainty words per 1k words
- `net_certainty: float`     # certainty_ratio - hedge_ratio

## Tools used
- Pure Python (regex/tokenize). Wordlists inline (Loughran-McDonald-inspired):
  HEDGE = {"may","might","could","possibly","approximately","uncertain","believe",
  "expect","hope","appears","likely","potential","subject to","depends"}
  CERTAINTY = {"will","definitely","clearly","confident","strong","record",
  "certainly","committed","guarantee","robust","exceeded"}

## Agent responsible
Sentiment & Tone Analyst.

## Procedure
1. Lowercase, tokenize words.
2. Count hedge/certainty hits; normalize per 1,000 tokens.
3. net_certainty = certainty_ratio - hedge_ratio.

## Edge cases / notes
- Compute SEPARATELY for prepared remarks vs Q&A — Q&A hedging spikes are the signal.
- Negations ("not confident") are not handled by a flat wordlist; flag as a known limit.