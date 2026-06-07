---
name: finbert-tone-analysis
description: Scores financial text sentiment (positive/negative/neutral) using the FinBERT model, aggregated to a single tone score per segment. Use whenever earnings text, prepared remarks, or Q&A needs calibrated finance-domain sentiment rather than generic LLM sentiment.
---

# FinBERT Tone / Sentiment Analysis

## Purpose
Compute a continuous tone score in [-1, +1] = P(positive) - P(negative), per segment.

## Inputs
- `text: str` (or list of sentences)

## Outputs
- `tone_score: float`            # mean over sentences of (p_pos - p_neg)
- `label_distribution: dict`     # {"positive": n, "negative": n, "neutral": n}

## Tools used
- transformers: `pipeline("text-classification", model="ProsusAI/finbert",
  truncation=True, max_length=512, top_k=None)`.

## Agent responsible
Sentiment & Tone Analyst.

## Procedure
1. Sentence-split text (nltk or regex on `[.!?]`).
2. Run the pipeline per sentence with `truncation=True, max_length=512`.
3. tone = mean(p_positive - p_negative). FinBERT returns labels positive/negative/neutral.

## Edge cases / notes
- 512-token cap: long monologues must be sentence-chunked, never truncated whole.
- Load the model once at module scope (cold start ~ download + init).
- Alternative `yiyanghkust/finbert-tone` (analyst-report tuned) maps LABEL_0=neutral,
  LABEL_1=positive, LABEL_2=negative — handle label maps explicitly.