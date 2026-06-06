---
name: api_integration
description: "Generic API calling with retries, rate-limit handling, and schema validation. Use when: agents need to call external APIs (SEC EDGAR, financial data providers, etc.)."
---

# API Integration Skill

Enables safe, resilient API calls from agents.

## Features

- **Retries**: Exponential backoff with jitter
- **Rate limits**: Honor X-RateLimit headers, circuit breaker
- **Schema validation**: Validate responses against Pydantic schemas
- **Timeouts**: Configurable per-call timeout
- **Secrets**: Use environment variables for API keys

## Tools

- `http_get`: GET request with retries
- `http_post`: POST request with retries
- `validate_response`: Validate response against schema

## Output

Returns validated response or error with retry details.
