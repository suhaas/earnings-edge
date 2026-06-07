from __future__ import annotations

import operator
from typing import Annotated, Any, TypedDict

from pydantic import BaseModel, Field


class EarningsKPIs(BaseModel):
    """Structured KPIs extracted from earnings text. Null any field not explicitly stated."""

    revenue_actual: float | None = Field(None, description="Reported revenue in USD (numeric).")
    eps_actual: float | None = Field(None, description="Reported diluted EPS in USD.")
    revenue_guidance_next_q: float | None = Field(
        None, description="Guided next-quarter revenue USD."
    )
    eps_guidance_next_q: float | None = Field(None, description="Guided next-quarter EPS USD.")
    guidance_language: str = Field(
        "not provided", description="Verbatim guidance phrasing or 'not provided'."
    )
    segment_revenue: dict[str, float] = Field(
        default_factory=dict, description="Segment -> revenue USD."
    )


class SurpriseSignal(BaseModel):
    """Fused, transparent signal."""

    score: float = Field(..., description="Signal score in [-100, 100].")
    direction: str = Field(..., description="'bullish' | 'bearish' | 'neutral'.")
    confidence: float = Field(..., description="Confidence in [0, 1].")
    rationale: str = Field(..., description="Plain-English explanation of the weighted score.")
    brief_markdown: str = Field("", description="Rendered analyst brief.")


class EarningsState(TypedDict, total=False):
    ticker: str
    year: int
    quarter: int
    user_id: str
    transcript_prepared: str
    transcript_qa: str
    transcript_source: str
    press_release_text: str
    sentiment: Annotated[list[dict[str, Any]], operator.add]
    kpis: Annotated[list[dict[str, Any]], operator.add]
    signal: dict[str, Any]
    brief_markdown: str
    grounding_score: float
    grounding_comment: str
    revision_count: int
    delivery_log: Annotated[list[str], operator.add]
    errors: Annotated[list[str], operator.add]
