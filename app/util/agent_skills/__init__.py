# -*- coding: UTF-8 -*-
"""Agent Skills — progressive disclosure prompt modules.

Each skill is a standalone string that gets injected into the system prompt
only when the user's intent matches that domain.
"""

from app.util.agent_skills.canvas_skill import CANVAS_SKILL
from app.util.agent_skills.blueprint_skill import BLUEPRINT_SKILL
from app.util.agent_skills.file_skill import FILE_SKILL
from app.util.agent_skills.mindmap_skill import MINDMAP_SKILL
from app.util.agent_skills.code_skill import CODE_SKILL

__all__ = [
    "CANVAS_SKILL", "BLUEPRINT_SKILL", "FILE_SKILL",
    "MINDMAP_SKILL", "CODE_SKILL", "get_skills_for_intent",
]

# Tier 1: Keyword-based domain matching (core skills)
CORE_SKILL_MAP = {
    "canvas": lambda: CANVAS_SKILL,
    "blueprint": lambda: BLUEPRINT_SKILL,
    "file": lambda: FILE_SKILL,
    "mindmap": lambda: MINDMAP_SKILL,
    "code": lambda: CODE_SKILL,
}

# Tier 2: Context-aware snippets
CONTEXT_TRIGGERS = {
    "has_failures": (lambda: "\n\n[!] 前方步骤有失败，请尝试替代方案或跳过该步骤。", "错误恢复"),
}


def get_skills_for_intent(intents: list[str], context: dict = None) -> str:
    """Return combined skill prompts for the given intent tags.

    Tier 1: Keyword-based domain matching (core skills).
    Tier 2: Context-aware snippets based on execution state.

    Args:
        intents: list of intent tags, e.g. ["canvas", "blueprint"].
        context: optional dict with execution state flags:
            - has_failures: bool — current execution has had tool failures

    Returns:
        Concatenated skill prompt string, or empty string if no match.
    """
    context = context or {}
    parts = []

    # Tier 1: Core skills by keyword domain
    for tag in intents:
        if tag == "general":
            continue
        sk = CORE_SKILL_MAP.get(tag)
        if sk:
            parts.append(sk())

    # Tier 2: Context-aware snippets
    if context.get("has_failures"):
        snippet_fn, _ = CONTEXT_TRIGGERS["has_failures"]
        parts.append(snippet_fn())

    return "\n\n".join(parts) if parts else ""
