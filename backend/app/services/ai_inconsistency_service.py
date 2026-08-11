"""Optional AI suggestions for biometric inconsistencies."""

from __future__ import annotations

import json
from typing import Any

from app.core.config import settings


class AISuggestionService:
    def suggest(self, marks: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not self._enabled(marks):
            return []

        try:
            from openai import OpenAI
        except ImportError:
            return []

        schema = {
            "type": "object",
            "properties": {
                "issues": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "mark_id": {"type": ["integer", "null"]},
                            "issue_type": {
                                "type": "string",
                                "enum": [
                                    "duplicate",
                                    "missing_pair",
                                    "late_pattern",
                                    "suspicious_sequence",
                                    "format_warning",
                                ],
                            },
                            "description": {"type": "string"},
                            "confidence": {
                                "type": "number",
                                "minimum": 0,
                                "maximum": 1,
                            },
                        },
                        "required": [
                            "mark_id",
                            "issue_type",
                            "description",
                            "confidence",
                        ],
                        "additionalProperties": False,
                    },
                }
            },
            "required": ["issues"],
            "additionalProperties": False,
        }

        client = OpenAI(api_key=settings.openai_api_key)
        try:
            response = client.chat.completions.create(
                model=settings.ai_model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You only suggest attendance inconsistencies. "
                            "Never approve, correct, or write data. Return only "
                            "issues that match the schema."
                        ),
                    },
                    {
                        "role": "user",
                        "content": json.dumps(
                            {"marks": marks[:200]}, ensure_ascii=False, default=str
                        ),
                    },
                ],
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "attendance_inconsistency_suggestions",
                        "schema": schema,
                        "strict": True,
                    },
                },
            )
        except Exception:
            return []

        content = response.choices[0].message.content or "{}"
        try:
            payload = json.loads(content)
        except json.JSONDecodeError:
            return []

        issues = []
        for issue in payload.get("issues", []):
            if issue.get("confidence", 0) < settings.ai_min_confidence:
                continue
            issues.append(
                {
                    "mark_id": issue.get("mark_id"),
                    "issue_type": issue["issue_type"],
                    "description": issue["description"],
                    "status": "pending",
                    "source": "ai",
                    "confidence": issue.get("confidence"),
                }
            )
        return issues

    def _enabled(self, marks: list[dict[str, Any]]) -> bool:
        return bool(
            marks
            and settings.ai_enabled
            and settings.ai_provider.lower() == "openai"
            and settings.ai_model
            and settings.openai_api_key
        )


ai_suggestion_service = AISuggestionService()
