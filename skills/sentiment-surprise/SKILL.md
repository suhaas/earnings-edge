---
name: sentiment-surprise
description: Computes a sentiment surprise by comparing the current quarter's tone against the trailing eight-quarter mean stored in long-term memory. Use whenever the analysis needs tone change relative to history, not just an absolute tone score.
---

# Sentiment-Surprise Computation (vs trailing 8-quarter mean)

## Purpose
Express this quarter's tone as a z-like deviation from the company's own history.

## Inputs
- `ticker: str`, `current_tone: float`

## Outputs
- `sentiment_surprise: float`    # current_tone - trailing_mean
- `trailing_mean: float`, `n_quarters: int`

## Tools used
- LangGraph BaseStore: `store.search(("sentiment_history", ticker))`,
  `store.put(("sentiment_history", ticker), f"{year}Q{quarter}", {"tone": ...})`.

## Agent responsible
Sentiment & Tone Analyst (read) + Delivery agent (write current quarter).

## Procedure
1. `items = store.search(("sentiment_history", ticker), limit=8)`.
2. trailing_mean = mean of stored tones (skip current quarter).
3. sentiment_surprise = current_tone - trailing_mean (if n_quarters >= 2, else 0.0).

## Edge cases / notes
- Cold start: < 2 prior quarters -> return surprise 0.0 and confidence penalty downstream.
- The Store is cross-thread; the checkpointer is per-thread — they are different objects. 
- Write the current quarter only AFTER successful delivery, to avoid polluting history on failed runs.