"""Guard the prompt/registry/agent invariant so the desyncs we just fixed can't recur.

Three drift classes this catches automatically:
  1. Role-set drift  — agent roles, registry roles, and prompt folders must be identical.
  2. Missing prompt  — every registry `active_version` must have a matching prompts/<role>/v<N>.md.
  3. Stale content   — each prompt's H1 title must name its own role (catches a prompt body
                       copied from a different agent, e.g. ingestion/v1.md titled "Analyst Agent").

These checks are hermetic (filesystem + YAML only) — no imports of the heavy agent modules.
"""

from __future__ import annotations

import pathlib

import pytest
import yaml

_ROOT = pathlib.Path(__file__).resolve().parents[2]
_PROMPTS = _ROOT / "prompts"
_AGENTS = _ROOT / "src" / "agentic_app" / "agents"


def _agent_roles() -> set[str]:
    return {p.stem.removesuffix("_agent") for p in _AGENTS.glob("*_agent.py")}


def _registry() -> dict[str, dict]:
    data = yaml.safe_load((_PROMPTS / "registry.yaml").read_text(encoding="utf-8"))
    return data["roles"]


def _prompt_dirs() -> set[str]:
    return {p.name for p in _PROMPTS.iterdir() if p.is_dir() and p.name != "shared"}


def test_roles_match_across_agents_registry_and_prompts() -> None:
    agents, registry, dirs = _agent_roles(), set(_registry()), _prompt_dirs()
    assert agents == registry, f"agent roles {agents} != registry roles {registry}"
    assert agents == dirs, f"agent roles {agents} != prompt folders {dirs}"


def test_every_registry_active_version_has_a_prompt_file() -> None:
    missing = [
        f"prompts/{role}/{meta['active_version']}.md"
        for role, meta in _registry().items()
        if not (_PROMPTS / role / f"{meta['active_version']}.md").is_file()
    ]
    assert not missing, f"registry points at missing prompt files: {missing}"


@pytest.mark.parametrize("role", sorted(_registry()))
def test_prompt_h1_names_its_role(role: str) -> None:
    """The first H1 of prompts/<role>/v<active>.md must mention <role> (case-insensitive).

    This is the cheap heuristic that would have flagged the stale bodies — e.g. a file at
    prompts/ingestion/v1.md whose title said "Analyst Agent".
    """
    version = _registry()[role]["active_version"]
    text = (_PROMPTS / role / f"{version}.md").read_text(encoding="utf-8")
    h1 = next((ln for ln in text.splitlines() if ln.startswith("# ")), "")
    assert role.lower() in h1.lower(), (
        f"prompts/{role}/{version}.md H1 {h1!r} does not name its role '{role}' "
        f"(likely a stale prompt copied from another agent)"
    )
