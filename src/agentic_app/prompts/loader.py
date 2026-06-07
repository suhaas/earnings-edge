"""Prompt loading and rendering.

Resolves an agent role to its active, fully-rendered system prompt:

    role -> registry.yaml active_version -> prompts/<role>/v<N>.md -> expand {{shared.*}}

Include syntax inside a prompt file:
  - ``{{shared.safety}}``              -> the whole prompts/shared/safety.md
  - ``{{shared.output_formats.json}}`` -> the "json" section of prompts/shared/output_formats.md
    (the markdown heading whose text contains the selector, down to the next same/higher heading)

The rendered result is cached per role. The prompts directory is resolved from the repo
layout by default; override with the ``PROMPTS_DIR`` env var or the constructor argument.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

import yaml

_INCLUDE = re.compile(r"\{\{\s*shared\.([A-Za-z0-9_.]+)\s*\}\}")


class PromptError(Exception):
    """Raised when a prompt, role, or shared include cannot be resolved."""


class PromptLoader:
    """Load and render versioned prompts from the ``prompts/`` directory."""

    def __init__(self, prompts_dir: Path | None = None) -> None:
        env_dir = os.environ.get("PROMPTS_DIR")
        self._dir = prompts_dir or Path(env_dir or Path(__file__).resolve().parents[3] / "prompts")
        self._cache: dict[str, str] = {}

    def load(self, role: str) -> str:
        """Return the active, fully-rendered system prompt for ``role``."""
        if role not in self._cache:
            self._cache[role] = self._render(role)
        return self._cache[role]

    # -- internals -------------------------------------------------------------

    def _registry(self) -> dict[str, Any]:
        path = self._dir / "registry.yaml"
        if not path.is_file():
            raise PromptError(f"registry not found: {path}")
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        return {str(k): v for k, v in data.get("roles", {}).items()}

    def _render(self, role: str) -> str:
        roles = self._registry()
        if role not in roles:
            raise PromptError(f"unknown role '{role}' (registry roles: {sorted(roles)})")
        version = roles[role]["active_version"]
        path = self._dir / role / f"{version}.md"
        if not path.is_file():
            raise PromptError(f"missing prompt file for role '{role}': {path}")
        return self._expand(path.read_text(encoding="utf-8")).strip() + "\n"

    def _expand(self, text: str) -> str:
        return _INCLUDE.sub(lambda m: self._shared(m.group(1)), text)

    def _shared(self, key: str) -> str:
        head, _, selector = key.partition(".")
        path = self._dir / "shared" / f"{head}.md"
        if not path.is_file():
            raise PromptError(f"missing shared include 'shared.{key}': {path}")
        content = path.read_text(encoding="utf-8")
        if selector:
            content = self._section(content, selector, key)
        return content.strip()

    @staticmethod
    def _section(content: str, selector: str, key: str) -> str:
        """Return the markdown section whose heading text contains ``selector``."""
        out: list[str] = []
        level = 0
        capturing = False
        for line in content.splitlines():
            if line.startswith("#"):
                depth = len(line) - len(line.lstrip("#"))
                heading = line.lstrip("#").strip().lower()
                if not capturing and selector.lower() in heading:
                    capturing, level = True, depth
                    out.append(line)
                    continue
                if capturing and depth <= level:
                    break
            if capturing:
                out.append(line)
        if not out:
            raise PromptError(f"section '{selector}' not found for include 'shared.{key}'")
        return "\n".join(out)


prompt_loader = PromptLoader()
