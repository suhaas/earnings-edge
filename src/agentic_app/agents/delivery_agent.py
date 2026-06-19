"""Delivery agent: ship the analyst brief (Slack/Notion/email) and log it."""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Any

from composio import Composio
from composio_langchain import LangchainProvider
from langchain.agents import create_agent
from langchain_anthropic import ChatAnthropic
from langchain_core.runnables import RunnableConfig
from langgraph.store.base import BaseStore

from agentic_app.orchestration.state import EarningsState
from agentic_app.prompts.loader import prompt_loader


@lru_cache(maxsize=1)
def _composio() -> Any:
    """Composio client, built lazily so import needs no COMPOSIO_API_KEY."""
    return Composio(provider=LangchainProvider())


@lru_cache(maxsize=1)
def _llm() -> Any:
    """Chat model, built lazily so importing this module needs no API key."""
    return ChatAnthropic(model="claude-sonnet-4-5", temperature=0)  # type: ignore[call-arg]


def deliver_node(
    state: EarningsState, config: RunnableConfig, *, store: BaseStore
) -> dict[str, Any]:
    user_id = state.get("user_id", os.environ.get("COMPOSIO_USER_ID", "default"))

    log: list[str] = []
    if not os.environ.get("COMPOSIO_API_KEY"):
        # No Composio configured -> skip distribution instead of crashing the run.
        # The brief was already produced upstream; we just don't ship it anywhere.
        # Set COMPOSIO_API_KEY (+ connect Slack/Notion/Sheets/Gmail) to enable delivery.
        log.append("delivery skipped (COMPOSIO_API_KEY not set)")
    else:
        # Everything Composio-related is guarded: a bad key, an unconnected Gmail
        # account, or a network/TLS failure logs an error instead of crashing the run,
        # so the brief still surfaces upstream.
        try:
            session = _composio().create(
                user_id=user_id,
                # Full multi-channel delivery — restore when those accounts are connected:
                # toolkits=["slack", "notion", "googlesheets", "gmail"],
                toolkits=["gmail"],  # first sample: email only
            )
            tools = session.tools()  # LangChain StructuredTools, auth handled by Composio
            agent = create_agent(
                model=_llm(),
                tools=tools,
                system_prompt=prompt_loader.load("delivery"),
            )
            sig = state.get("signal", {})
            task = (
                f"Ticker {state['ticker']} Q{state['quarter']} FY{state['year']}. "
                f"Signal score {sig.get('score')} ({sig.get('direction')}, "
                f"confidence {sig.get('confidence')}).\n\nBRIEF:\n{state.get('brief_markdown', '')}"
            )
            result = agent.invoke({"messages": [("user", task)]})  # type: ignore[call-overload]
            log.append(result["messages"][-1].content[:500])
        except Exception as e:
            log.append(f"delivery error: {e}")

    # ---- write current-quarter tone to long-term memory (sentiment-surprise) ----
    s = (state.get("sentiment") or [{}])[-1]
    if "current_tone" in s:
        store.put(
            ("sentiment_history", state["ticker"]),
            f"{state['year']}Q{state['quarter']}",
            {"tone": s["current_tone"]},
        )
    return {"delivery_log": log}


# from agentic_app.orchestration.state import EarningsState


# def deliver_node(state: EarningsState) -> dict:
#     """Deliver the brief and record a delivery log entry (reducer appends).

#     TODO: Composio-backed delivery (see skills/composio-delivery).
#     TODO: add a `store: BaseStore` parameter to read/write the injected Store.
#     """
#     return {"delivery_log": ["stub delivery"]}
