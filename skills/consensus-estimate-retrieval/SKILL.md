---
name: consensus-estimate-retrieval
description: Retrieves analyst consensus EPS and revenue estimates from yfinance for surprise calculations. Use whenever actual results must be compared against the street's expectations.
---

# Consensus Estimate Retrieval (yfinance)

## Purpose
Fetch consensus EPS/revenue estimates and historical surprises.

## Inputs
- `ticker: str`

## Outputs
- consensus_eps: float|None, consensus_revenue: float|None
- recent_surprise_pct: float|None

## Tools used
- yfinance: `Ticker(t).get_earnings_estimate()` (cols numberOfAnalysts, avg, low, high,
  yearAgoEps, growth; index 0q,+1q,0y,+1y); `.get_revenue_estimate()`;
  `.earnings_history` (epsEstimate, epsActual, surprisePercent).

## Agent responsible
KPI Delta Extractor.

## Procedure
1. consensus_eps = get_earnings_estimate().loc["0q","avg"].
2. consensus_revenue = get_revenue_estimate().loc["0q","avg"].
3. recent_surprise_pct = earnings_history["surprisePercent"].iloc[-1].

## Edge cases / notes
- yfinance is UNOFFICIAL — field names and shapes change; wrap every access in try/except
  and fall back to `.info.get("forwardEps")`.
- Rate limiting (HTTP 429): add jitter/sleep or cache with requests-cache. 
- "0q" is the current quarter estimate; "+1q" is next quarter (used for guidance compare).