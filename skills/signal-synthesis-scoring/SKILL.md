---
name: signal-synthesis-scoring
description: Combines sentiment surprise, hedging, EPS/revenue surprise, and guidance into a single transparent weighted score with direction and confidence. Use whenever the per-agent features must be fused into one actionable signal.
---

# Signal Synthesis & Scoring

## Purpose
Produce a SurpriseSignal(score in [-100,100], direction, confidence in [0,1]).

## Inputs
- sentiment_surprise, net_certainty (qa), eps_surprise_pct, revenue_surprise_pct,
  has_guidance_raise

## Outputs (SurpriseSignal schema)
- score: float, direction: "bullish"|"bearish"|"neutral", confidence: float, rationale: str

## Tools used
- Pure Python weighted model (transparent, auditable). No black-box ML.

## Agent responsible
Signal Synthesis & Report agent.

## Procedure (transparent weights)
- score = 100 * tanh( 0.35*z(eps_surprise_pct) + 0.20*z(revenue_surprise_pct)
          + 0.20*sentiment_surprise + 0.10*net_certainty_qa + 0.15*(+1 if raise else 0) )
- direction = sign(score) thresholded at +/-10.
- confidence = f(#non-null inputs, n_quarters of history); penalize cold start.

## Edge cases / notes
- Document weights in the brief so the score is explainable (no hidden model).
- Missing inputs reduce confidence rather than defaulting to 0 silently.