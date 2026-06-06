---
name: /add-tool
description: "Create a new tool (atomic capability). Scaffolds {capability}.py, schema in schemas.py, unit test, and auto-registration."
---

# Add a New Tool

When adding a tool, follow these steps:

## 1. Define the Tool
Create `src/tools/{capability}.py` with:
- A function decorated `@tool_registry.register()`
- Type hints for all args/returns
- Docstring explaining purpose

Example:
```python
from agentic_app.tools.registry import tool_registry
from agentic_app.config.logging import logger

@tool_registry.register()
async def fetch_earnings(ticker: str, fiscal_year: int) -> dict[str, Any]:
    """Fetch earnings data for a given ticker and fiscal year.
    
    Args:
        ticker: Stock ticker symbol (e.g., 'AAPL')
        fiscal_year: Fiscal year to fetch (e.g., 2024)
    
    Returns:
        Dict with revenue, earnings, guidance, etc.
    """
    logger.info("fetching_earnings", ticker=ticker, fiscal_year=fiscal_year)
    # Implementation...
    return result
```

## 2. Define the Schema
Add to `src/tools/schemas.py`:
```python
from pydantic import BaseModel, Field

class FetchEarningsInput(BaseModel):
    ticker: str = Field(..., description="Stock ticker symbol")
    fiscal_year: int = Field(..., description="Fiscal year")

class FetchEarningsOutput(BaseModel):
    revenue: float
    earnings: float
    guidance: str
```

## 3. Register & Error Handling
- Tool is auto-collected by `@tool_registry.register()`
- Wrap errors in `ToolError(category="...", message="...", details={...})`
- Agent logs the error in message history for LLM visibility

## 4. Test
Create `tests/unit/test_tools/test_fetch_earnings.py`:
```python
@pytest.mark.asyncio
async def test_fetch_earnings_valid(fake_anthropic):
    """No network; mock the call."""
    from agentic_app.tools.fetch_earnings import fetch_earnings
    
    result = await fetch_earnings(ticker="AAPL", fiscal_year=2024)
    assert result["revenue"] > 0
    assert result["earnings"] > 0
```

## 5. Document
Add entry to `AGENTS.md` → Common Agent Tasks section.

---

See `AGENTS.md` for architecture and tool naming conventions.
