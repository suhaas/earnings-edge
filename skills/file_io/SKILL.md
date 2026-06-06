---
name: file_io
description: "Scoped file I/O: read, write, and manage files safely. Use when: agents need to work with local files, process documents, or persist data."
---

# File I/O Skill

Enables safe, scoped file operations for agents.

## Features

- **Path allowlisting**: Only access whitelisted directories
- **Read/write**: Load and save files atomically
- **Format detection**: Auto-detect YAML, JSON, CSV, text
- **Backups**: Automatic backup before overwrite

## Tools

- `file_read`: Read file contents
- `file_write`: Write file (with backup)
- `file_list`: List directory contents
- `file_delete`: Remove file (with confirmation)

## Output

Returns file contents or operation status with error details.
