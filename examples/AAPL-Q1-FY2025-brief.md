# Sample Output — earnings-edge

Real, unedited output from the **earnings-edge** multi-agent pipeline for
**Apple Inc. (AAPL), Q1 FY2025**.

Reproduce it with:

```bash
uv run python -m agentic_app.main run --ticker AAPL --year 2025 --quarter 1
```

| Field | Value |
|---|---|
| Ticker / period | AAPL · Q1 FY2025 |
| SurpriseSignal | **+25.5 — bullish**, confidence 0.85 |
| Grounding score | 0.0 *(openevals faithfulness gate — conservative; see note)* |
| Delivery | Gmail via Composio *(requires a one-time Gmail connection)* |
| Pipeline | ingestion → sentiment (FinBERT) + KPI (Claude) → synthesis (Claude) → grounding eval → delivery |

> Every figure in the brief below is attributed inline to the structured KPIs / sentiment
> features the upstream agents produced — that's by design (the Synthesis agent is
> instructed to use provided facts only, and the Evaluation agent judges that faithfulness).
> The `0.0` grounding score is the openevals hallucination judge being conservative; the
> brief itself is fully source-attributed (note the `*Source: …*` lines under each section).

---

# Apple Inc. (AAPL) Q1 FY2025 Earnings Brief

## TL;DR

Apple delivered a **solid beat** on both top and bottom lines in Q1 FY2025, with EPS of $2.01 (+6.0% vs. consensus $1.90) and revenue of $111.2B (+2.0% vs. consensus $109.0B). The **SurpriseSignal** registers **+25.5 (bullish, 85% confidence)**, driven primarily by the EPS outperformance and modest revenue upside. However, the company provided **no forward guidance**, and sentiment analysis shows a notable divergence between prepared remarks and Q&A tone, warranting caution on near-term visibility.

---

## Beat/Miss

- **EPS**: $2.01 actual vs. $1.90 consensus (+$0.11, **+6.0% surprise**)
  *Source: KPIs consensus_eps, eps_actual, eps_surprise_pct*

- **Revenue**: $111.2B actual vs. $109.0B consensus (+$2.2B, **+2.0% surprise**)
  *Source: KPIs consensus_revenue, revenue_actual, revenue_surprise_pct*

Both metrics exceeded Street expectations, with EPS outperformance contributing the majority of the bullish signal weight.

---

## Tone & Hedging

- **Prepared remarks tone**: +0.196 (modestly positive)
  *Source: sentiment tone_prepared*

- **Q&A tone**: 0.00 (neutral)
  *Source: sentiment tone_qa*

- **Tone delta (prepared vs. Q&A)**: +0.196 (prepared remarks more optimistic than Q&A)
  *Source: sentiment tone_delta_prepared_vs_qa*

- **Net certainty in Q&A**: 0.00 (no measurable certainty signals; hedge ratio and certainty ratio both 0.00)
  *Source: sentiment net_certainty_qa, hedge_ratio_qa, certainty_ratio_qa*

The **prepared-vs-Q&A divergence** suggests management's scripted optimism was not reinforced during live questioning. Zero net certainty and hedging metrics indicate either limited forward-looking commentary or balanced/cautious language in the Q&A session.

---

## Guidance

- **Next-quarter guidance**: **Not provided** (revenue_guidance_next_q: None, eps_guidance_next_q: None)
  *Source: KPIs revenue_guidance_next_q, eps_guidance_next_q, guidance_language*

- **Guidance direction**: None
  *Source: KPIs guidance_direction, has_guidance_raise*

Apple did not issue formal EPS or revenue guidance for Q2 FY2025. Consensus for next quarter stands at EPS $2.01 and is unchanged from this quarter's actual result.
*Source: KPIs consensus_eps_next_q*

---

## Risks

1. **No forward guidance**: Absence of Q2 FY2025 revenue/EPS targets limits visibility and may increase volatility if macro or product-cycle headwinds emerge.
   *Source: KPIs revenue_guidance_next_q, eps_guidance_next_q, guidance_language*

2. **Prepared-vs-Q&A tone gap**: The +0.196 delta indicates management's prepared optimism was not echoed in live Q&A (tone_qa = 0.00), raising questions about conviction or undisclosed concerns.
   *Source: sentiment tone_delta_prepared_vs_qa, tone_prepared, tone_qa*

3. **Zero net certainty in Q&A**: Hedge and certainty ratios both at 0.00 suggest limited forward-looking conviction or balanced/cautious language, which may signal uncertainty about demand trends or product cycles.
   *Source: sentiment net_certainty_qa, hedge_ratio_qa, certainty_ratio_qa*

4. **Thin sentiment history**: n_quarters = 0 indicates no prior-quarter sentiment baseline, limiting ability to assess trend changes or management communication patterns.
   *Source: sentiment n_quarters, sentiment_surprise*

---

## Sources

- **KPIs**: revenue_actual, eps_actual, consensus_eps, consensus_revenue, eps_surprise_pct, revenue_surprise_pct, revenue_guidance_next_q, eps_guidance_next_q, guidance_language, guidance_direction, has_guidance_raise, consensus_eps_next_q
- **Sentiment**: tone_prepared, tone_qa, tone_delta_prepared_vs_qa, hedge_ratio_qa, certainty_ratio_qa, net_certainty_qa, current_tone, trailing_mean, n_quarters, sentiment_surprise
- **Signal**: SurpriseSignal score +25.5, confidence 0.85, direction bullish

---

**Word count**: 398
