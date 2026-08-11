"""Optional AI helper to normalize biometric text exports."""

from __future__ import annotations

import json
import csv
from dataclasses import dataclass
from decimal import Decimal
from io import StringIO
from typing import Any

from app.core.config import settings


@dataclass(frozen=True)
class AINormalizationResult:
    csv_text: str
    source: str
    provider: str | None = None
    model: str | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: Decimal = Decimal("0")


class AIBiometricNormalizerService:
    PRICE_PER_MILLION_TOKENS = {
        "gpt-5.2": {
            "input": Decimal("1.75"),
            "output": Decimal("14.00"),
        }
    }

    def normalize_to_csv(self, text: str) -> AINormalizationResult | None:
        if not self._enabled(text):
            return None

        try:
            from openai import OpenAI
        except ImportError:
            return None

        delimiter = self._detect_delimiter(text)
        reader = csv.DictReader(StringIO(text), delimiter=delimiter)
        source_fields = [field.strip() for field in (reader.fieldnames or []) if field]
        if not source_fields:
            return None

        local_csv = self._infer_locally_to_csv(text, delimiter, source_fields)
        if local_csv:
            return AINormalizationResult(csv_text=local_csv, source="local_fallback")

        sample = "\n".join(text.splitlines()[:25])
        schema = {
            "type": "object",
            "properties": {
                "field_map": {
                    "type": "object",
                    "properties": {
                        "dni": {"type": "string"},
                        "last_names": {"type": "string"},
                        "first_names": {"type": "string"},
                        "marked_at": {"type": "string"},
                        "mark_type": {"type": "string"},
                    },
                    "required": [
                        "dni",
                        "last_names",
                        "first_names",
                        "marked_at",
                        "mark_type",
                    ],
                    "additionalProperties": False,
                    "description": (
                        "Map canonical fields to the exact source column names. "
                        "Use an empty string when the source file does not provide "
                        "last_names or first_names."
                    ),
                }
            },
            "required": ["field_map"],
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
                            "Identify biometric attendance export columns. Return "
                            "only a field mapping. Do not invent source column names. "
                            "DNI identifies the person, marked_at is the date/time "
                            "of the punch, and mark_type indicates entry or exit."
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Source columns: {source_fields}\n\n"
                            f"Sample rows:\n{sample}"
                        ),
                    },
                ],
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "biometric_import_normalized_csv",
                        "schema": schema,
                        "strict": True,
                    },
                },
            )
        except Exception:
            local_csv = self._infer_locally_to_csv(text, delimiter, source_fields)
            if local_csv:
                return AINormalizationResult(
                    csv_text=local_csv, source="local_fallback"
                )
            return None

        content = response.choices[0].message.content or "{}"
        try:
            payload: dict[str, Any] = json.loads(content)
        except json.JSONDecodeError:
            return None
        field_map = payload.get("field_map")
        if not isinstance(field_map, dict):
            local_csv = self._infer_locally_to_csv(text, delimiter, source_fields)
            if local_csv:
                return AINormalizationResult(
                    csv_text=local_csv, source="local_fallback"
                )
            return None
        csv_text = self._normalize_with_field_map(text, delimiter, field_map)
        if not csv_text:
            return None
        usage = getattr(response, "usage", None)
        input_tokens = int(getattr(usage, "prompt_tokens", 0) or 0)
        output_tokens = int(getattr(usage, "completion_tokens", 0) or 0)
        total_tokens = int(getattr(usage, "total_tokens", 0) or 0)
        return AINormalizationResult(
            csv_text=csv_text,
            source="openai",
            provider="openai",
            model=settings.ai_model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            estimated_cost_usd=self._estimated_cost(
                settings.ai_model, input_tokens, output_tokens
            ),
        )

    def _infer_locally_to_csv(
        self, text: str, delimiter: str, source_fields: list[str]
    ) -> str | None:
        field_map = {
            "dni": self._pick_field(
                source_fields,
                "dni",
                "documento",
                "document",
                "codigo",
                "persona",
                "empleado",
                "worker",
                "employee",
            ),
            "last_names": self._pick_field(
                source_fields,
                "apellido",
                "apellidos",
                "paterno",
                "materno",
                "surname",
                "last",
            ),
            "first_names": self._pick_field(
                source_fields,
                "nombre",
                "nombres",
                "docente",
                "name",
                "first",
            ),
            "marked_at": self._pick_field(
                source_fields,
                "fecha",
                "hora",
                "marcacion",
                "biometrico",
                "timestamp",
                "time",
                "date",
            ),
            "mark_type": self._pick_field(
                source_fields,
                "sentido",
                "tipo",
                "entrada",
                "salida",
                "direction",
                "event",
            ),
        }
        return self._normalize_with_field_map(text, delimiter, field_map)

    def _pick_field(self, fields: list[str], *keywords: str) -> str:
        for field in fields:
            normalized = field.strip().lower()
            if any(keyword in normalized for keyword in keywords):
                return field
        return ""

    def _normalize_with_field_map(
        self, text: str, delimiter: str, field_map: dict[str, Any]
    ) -> str | None:
        required = ("dni", "marked_at", "mark_type")
        if any(not str(field_map.get(field) or "").strip() for field in required):
            return None

        output = StringIO()
        writer = csv.DictWriter(
            output,
            fieldnames=["dni", "apellidos", "nombres", "fecha_hora", "tipo_marca"],
            lineterminator="\n",
        )
        writer.writeheader()

        reader = csv.DictReader(StringIO(text), delimiter=delimiter)
        for row in reader:
            writer.writerow(
                {
                    "dni": self._value(row, field_map.get("dni")),
                    "apellidos": self._value(row, field_map.get("last_names")),
                    "nombres": self._value(row, field_map.get("first_names")),
                    "fecha_hora": self._value(row, field_map.get("marked_at")),
                    "tipo_marca": self._value(row, field_map.get("mark_type")),
                }
            )
        return output.getvalue()

    def _value(self, row: dict[str, str | None], source_field: Any) -> str:
        field = str(source_field or "").strip()
        if not field:
            return ""
        return (row.get(field) or "").strip()

    def _detect_delimiter(self, text: str) -> str:
        sample = text[:4096]
        try:
            return csv.Sniffer().sniff(sample, delimiters=",;\t|").delimiter
        except csv.Error:
            return ","

    def _estimated_cost(
        self, model: str, input_tokens: int, output_tokens: int
    ) -> Decimal:
        pricing = self.PRICE_PER_MILLION_TOKENS.get(model.lower())
        if not pricing:
            return Decimal("0")
        cost = (
            Decimal(input_tokens) * pricing["input"]
            + Decimal(output_tokens) * pricing["output"]
        ) / Decimal("1000000")
        return cost.quantize(Decimal("0.000001"))

    def _enabled(self, text: str) -> bool:
        return bool(
            text.strip()
            and settings.ai_enabled
            and settings.ai_provider.lower() == "openai"
            and settings.ai_model
            and settings.openai_api_key
        )


ai_biometric_normalizer_service = AIBiometricNormalizerService()
