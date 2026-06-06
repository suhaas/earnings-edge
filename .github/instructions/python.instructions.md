---
name: python-instructions
applyTo: ["**/*.py"]
description: "Rules for all Python files: strict typing, async-first, error wrapping, imports organization, no print(). Use when: modifying src/ files, adding agents, tools, or utility functions."
---

# Python Code Guidelines

## Typing & Async

- **All files**: Type-annotated args and returns; use `from __future__ import annotations` at top
- **Functions**: Prefer `async def`; use `await` for async I/O; avoid blocking calls in agent context
- **Pydantic**: Complex inputs/outputs → Pydantic models with field validation
- **Exceptions**: Create typed exceptions (`class ToolError(Exception):`); wrap library errors, don't swallow

## Imports

- **Root**: Use `src/` as the import root (configured in `pyproject.toml`)
- **Order**: stdlib → third-party → local imports
- **Avoid**: Circular imports; use Protocol or TYPE_CHECKING if needed
- **No**: `from src.foo import bar` syntax; just `from agentic_app.foo import bar`

## Logging & Output

- **No `print()`**: Use `logger` from `src/config/logging.py` for all output
- **Structured logs**: Always include context (request ID, trace ID, key fields)
- **Example**: `logger.info("agent_step", agent=role, tool_used=tool_name, tokens=count)`

## Error Handling

- **Tool errors**: Wrap in `ToolError(category="...", message="...", details={...})`
- **Agent logs errors in message history** for LLM visibility
- **Escalate**: Let the Critic decide whether to retry or fail, don't catch and ignore

## File Structure

```python
# Imports (stdlib → third-party → local)
from __future__ import annotations

import asyncio
from typing import Any
from datetime import datetime

import httpx
from pydantic import BaseModel, Field

from agentic_app.config.logging import logger
from agentic_app.tools.schemas import ToolOutput

# Type aliases (optional)
ResultType = dict[str, Any]

# Models
class MyInput(BaseModel):
    query: str = Field(..., description="...")

# Functions/classes
async def my_function(input: MyInput) -> ResultType:
    """Docstring with purpose, args, and return type."""
    logger.info("function_started", query=input.query)
    result = await some_async_call()
    return result
```

## Testing

- **Unit tests**: Mock everything; no network, no LLM calls
- **Integration tests**: Use vcr-style recorded responses for determinism
- **See**: `tests/README.md` for test structure and fixtures
