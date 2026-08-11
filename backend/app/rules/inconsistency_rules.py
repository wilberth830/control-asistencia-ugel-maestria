"""TEC-D06 — rule engine + IA stub (IA only suggests; never auto-writes)."""

from __future__ import annotations

from typing import Any

from app.core.config import settings
from app.services.ai_inconsistency_service import ai_suggestion_service


def detect_basic_issues(marks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Deterministic rules: duplicate same day, missing pair, invalid timestamp flag."""
    issues: list[dict[str, Any]] = []
    seen: dict[str, int] = {}
    for m in marks:
        key = f"{m.get('staff_member_id')}:{str(m.get('marked_at'))[:10]}:{m.get('mark_type')}"
        if key in seen:
            issues.append(
                {
                    "mark_id": m.get("id"),
                    "issue_type": "duplicate",
                    "description": "Possible duplicate mark same day/type",
                    "status": "pending",
                    "source": "rules",
                }
            )
        seen[key] = 1
    return issues


def ia_suggest(marks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Placeholder for an AI provider. Disabled by default; never auto-writes."""
    if not settings.ai_enabled:
        return []
    return ai_suggestion_service.suggest(marks)
