# Tool Use Policy

## When to Use Tools

- Call a tool when you need external data or to execute code
- Always provide clear input parameters
- Validate tool outputs before using in analysis

## Error Handling

- If a tool fails, log the error and explain to the user
- Retry with different parameters if appropriate
- If retriable, use exponential backoff
- Never swallow errors; escalate to the Critic for guidance

## Tool Errors

Tool errors are wrapped in a standard format:
- `category`: Type of error (validation, timeout, network, etc.)
- `message`: Human-readable description
- `details`: Debug information
