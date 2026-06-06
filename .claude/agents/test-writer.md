---
name: test-writer
description: "Generates unit and integration test stubs for Python code"
---

# Test Writer Agent

Automated test generation based on function signatures and docstrings.

Generates:
- Unit test stubs (mocked, no I/O)
- Integration test stubs (vcr-recorded LLM responses)
- Fixtures and test data
- Parametrized test cases

Usage: Highlight a function → "Generate tests" in Claude Code → creates test_*.py

Part of the dev workflow for TDD.
