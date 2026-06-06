---
name: memory_management
description: "Short-term and long-term memory operations. Use when: agents need to store facts, preferences, or session state across turns."
---

# Memory Management Skill

Enables agents to build and query persistent memory.

## Features

- **Short-term**: Windowed message history (token-budgeted)
- **Long-term**: Persistent fact store (Redis/Postgres backed)
- **Compaction**: Auto-summarize short-term memory when budget exceeded
- **Retrieval**: Query memory by keyword or semantic similarity

## Tools

- `memory_store`: Save a fact
- `memory_retrieve`: Query memory
- `memory_compact`: Compress short-term memory

## Output

Returns stored fact ID or retrieved memories.
