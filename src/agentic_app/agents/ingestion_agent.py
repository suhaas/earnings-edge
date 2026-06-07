"""Ingestion agent: fetch transcript + press release for a ticker/quarter."""

from __future__ import annotations

import os
import re
from functools import lru_cache
from typing import Any

from dotenv import load_dotenv
from earningscall import get_company
from edgar import Company, set_identity

from agentic_app.orchestration.state import EarningsState


@lru_cache(maxsize=1)
def _ensure_edgar_identity() -> None:
    """Register the SEC User-Agent identity once, on first ingest (not at import).

    Reads EDGAR_IDENTITY ("Name email@x.com") lazily so importing this module
    never requires the env var to be set.
    """
    load_dotenv()
    set_identity(os.environ["EDGAR_IDENTITY"])


QA_BOUNDARY = re.compile(
    r"(?i)(question[-\s]and[-\s]answer|we['’]?ll now (begin|take).{0,30}question"
    r"|operator.{0,40}(first|next) question|\[?\s*Q\s*&\s*A\s*\]?)"
)


def _regex_split(full_text: str) -> tuple[str, str]:
    m = QA_BOUNDARY.search(full_text)
    if not m:
        return full_text, ""
    return full_text[: m.start()].strip(), full_text[m.start() :].strip()


def ingest_node(state: EarningsState) -> dict[str, Any]:
    _ensure_edgar_identity()
    ticker, year, q = state["ticker"], state["year"], state["quarter"]
    prepared, qa, pr_text, source = "", "", "", ""

    # 1) Primary: earningscall level=4 (segmented). Free for AAPL/MSFT; key for 5000+.
    try:
        company = get_company(ticker)
        t = company.get_transcript(year=year, quarter=q, level=4)
        if t and getattr(t, "prepared_remarks", None):
            prepared = t.prepared_remarks or ""
            qa = t.questions_and_answers or ""
            source = "earningscall"
    except Exception as e:
        return_err = f"earningscall: {e}"  # noqa: F841

    # 2) Fallback: SEC 8-K Exhibit 99.1 via edgartools.
    if not prepared:
        try:
            filing = Company(ticker).get_filings(form="8-K").latest()
            ek = filing.obj()  # EightK
            if getattr(ek, "has_press_release", False) and ek.press_releases:
                pr_text = ek.press_releases[0].text()
            else:
                for ex in filing.exhibits:
                    if getattr(ex, "exhibit_number", "") == "99.1":
                        pr_text = ex.text()
                        break
            prepared, qa = _regex_split(pr_text or filing.text())
            source = "edgar_8k"
        except Exception as e:
            return {"errors": [f"ingest failed: {e}"]}

    return {
        "transcript_prepared": prepared,
        "transcript_qa": qa,
        "press_release_text": pr_text,
        "transcript_source": source or "regex_split",
    }


# from __future__ import annotations

# from agentic_app.orchestration.state import EarningsState


# def ingest_node(state: EarningsState) -> dict:
#     """Entry node. Populate transcript + press-release text into state.

#     TODO: wire SEC EDGAR 8-K retrieval + EarningsCall transcript ingestion
#     (see skills/sec-edgar-8k-retrieval, skills/transcript-ingestion-segmentation).
#     """
#     return {
#         "transcript_prepared": "",
#         "transcript_qa": "",
#         "transcript_source": "stub",
#         "press_release_text": "",
#     }
