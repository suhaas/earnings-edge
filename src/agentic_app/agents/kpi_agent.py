"""KPI agent: extract structured KPIs (revenue, EPS, guidance, segments)."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

import yfinance as yf
from langchain_anthropic import ChatAnthropic

from agentic_app.orchestration.state import EarningsKPIs, EarningsState
from agentic_app.prompts.loader import prompt_loader


@lru_cache(maxsize=1)
def _extractor() -> Any:
    """Structured-output extractor, built lazily so import needs no API key."""
    llm = ChatAnthropic(model="claude-sonnet-4-5", temperature=0)  # type: ignore[call-arg]
    return llm.with_structured_output(EarningsKPIs, method="json_schema")


def _consensus(ticker: str) -> dict[str, float | None]:
    out: dict[str, float | None] = {
        "consensus_eps": None,
        "consensus_revenue": None,
        "consensus_eps_next_q": None,
    }
    try:
        tk = yf.Ticker(ticker)
        ee = tk.get_earnings_estimate()
        out["consensus_eps"] = float(ee.loc["0q", "avg"])
        out["consensus_eps_next_q"] = float(ee.loc["+1q", "avg"])
        re_ = tk.get_revenue_estimate()
        out["consensus_revenue"] = float(re_.loc["0q", "avg"])
    except Exception:
        try:
            out["consensus_eps"] = float(yf.Ticker(ticker).info.get("forwardEps"))
        except Exception:
            pass
    return out


def _pct(actual: float | None, cons: float | None) -> float | None:
    if actual is None or cons is None or cons == 0:
        return None
    return (actual - cons) / abs(cons) * 100.0


def kpi_node(state: EarningsState) -> dict[str, Any]:
    text = (state.get("press_release_text", "") + "\n\n" + state.get("transcript_prepared", ""))[
        :18000
    ]
    try:
        kpis: EarningsKPIs = _extractor().invoke(
            [
                {"role": "system", "content": prompt_loader.load("kpi")},
                {"role": "user", "content": text},
            ]
        )
    except Exception as e:
        return {"errors": [f"kpi extraction: {e}"], "kpis": [{}]}

    c = _consensus(state["ticker"])
    eps_surp = _pct(kpis.eps_actual, c["consensus_eps"])
    rev_surp = _pct(kpis.revenue_actual, c["consensus_revenue"])

    direction = "none"
    if kpis.eps_guidance_next_q is not None and c["consensus_eps_next_q"]:
        diff = (
            (kpis.eps_guidance_next_q - c["consensus_eps_next_q"])
            / abs(c["consensus_eps_next_q"])
            * 100
        )
        direction = "raise" if diff > 1 else "cut" if diff < -1 else "maintain"
    elif any(w in kpis.guidance_language.lower() for w in ("rais", "increas", "above")):
        direction = "raise"

    return {
        "kpis": [
            {
                **kpis.model_dump(),
                **c,
                "eps_surprise_pct": eps_surp,
                "revenue_surprise_pct": rev_surp,
                "guidance_direction": direction,
                "has_guidance_raise": direction == "raise",
            }
        ]
    }


# from agentic_app.orchestration.state import EarningsState


# def kpi_node(state: EarningsState) -> dict:
#     """Extract KPIs into state. Returns a list (reducer appends).

#     TODO: structured KPI extraction into EarningsKPIs schema
#     (see skills/kpi-extraction, skills/consensus-estimate-retrieval).
#     """
#     return {"kpis": []}
