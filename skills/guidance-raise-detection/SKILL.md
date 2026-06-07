---
name: guidance-raise-detection
description: Detects whether management raised, lowered, or maintained forward guidance by comparing stated guidance to the prior consensus for the next period. Use whenever forward-looking guidance direction is a required signal.
---

# Guidance-Raise Detection

## Purpose
Classify guidance direction: raise / maintain / cut.

## Inputs
- eps_guidance_next_q (from KPI extraction), consensus next-quarter EPS ("+1q" avg)
- guidance_language: str

## Outputs
- has_guidance_raise: bool
- guidance_direction: "raise"|"maintain"|"cut"|"none"

## Tools used
- Pure Python + the guidance_language string.

## Agent responsible
KPI Delta Extractor.

## Procedure
1. If numeric guidance > consensus("+1q") by >1% -> "raise"; < -1% -> "cut"; else "maintain".
2. If no numeric guidance, classify from guidance_language keywords
   ("raising"/"increased" vs "lowering"/"reduced").
3. has_guidance_raise = (direction == "raise").

## Edge cases / notes
- Companies often guide ranges — compare midpoints.
- Language and numbers can conflict; prefer numbers, log the conflict.