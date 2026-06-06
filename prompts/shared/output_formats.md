# Shared Output Formats

## JSON Output Contract

All structured outputs must follow this format:

```json
{
  "type": "analysis|error|insight",
  "summary": "Brief description",
  "data": {},
  "timestamp": "ISO8601",
  "confidence": "high|medium|low",
  "sources": []
}
```

## Error Response

```json
{
  "type": "error",
  "category": "tool_error|validation_error|timeout",
  "message": "User-facing error message",
  "details": {}
}
```
