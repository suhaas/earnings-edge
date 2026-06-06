---
name: security-reviewer
description: "Identifies secrets, unsafe code, and privilege escalation risks"
---

# Security Reviewer Agent

Automated security review for Python code changes.

Scans for:
- Hardcoded credentials (API keys, passwords, tokens)
- Unsafe patterns (`eval()`, `exec()`, pickle deserialization)
- SQL injection (unsanitized string interpolation)
- Path traversal (unchecked file operations)
- Privilege escalation (sudo in subprocess, elevated permissions)
- Unvalidated input to dangerous functions

Part of `/review-pr` workflow.
