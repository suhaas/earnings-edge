---
name: earnings-surprise-detection
description: Computes EPS and revenue surprise percentages from actuals versus consensus. Use whenever a beat/miss magnitude is needed as a quantitative signal input.
---

# Earnings-Surprise Detection (EPS / revenue surprise %)

## Purpose
Compute beat/miss magnitudes.

## Inputs
- eps_actual, consensus_eps, revenue_actual, consensus_revenue

## Outputs
- eps_surprise_pct: float|None      # (actual-consensus)/abs(consensus)*100
- revenue_surprise_pct: float|None

## Tools used
- Pure Python arithmetic.

## Agent responsible
KPI Delta Extractor.

## Procedure
1. eps_surprise_pct = (eps_actual - consensus_eps)/abs(consensus_eps)*100.
2. revenue_surprise_pct analogous.

## Edge cases / notes
- Guard divide-by-zero and None on either side -> return None.
- Negative consensus EPS: use abs() in denominator so sign of surprise stays meaningful.