"""Oracle repository for AI usage during biometric imports."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

import oracledb

from app.repositories.oracle import OracleRepositoryError, oracle_connection


class AIUsageRepository:
    def record(self, data: dict[str, Any]) -> None:
        sql = """
            INSERT INTO ai_usage_log (
                biometric_import_id, file_name, provider, model_name,
                input_tokens, output_tokens, total_tokens, estimated_cost_usd
            ) VALUES (
                :biometric_import_id, :file_name, :provider, :model_name,
                :input_tokens, :output_tokens, :total_tokens, :estimated_cost_usd
            )
        """
        try:
            with oracle_connection() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        sql,
                        biometric_import_id=data["biometric_import_id"],
                        file_name=data["file_name"],
                        provider=data["provider"],
                        model_name=data["model_name"],
                        input_tokens=data.get("input_tokens", 0),
                        output_tokens=data.get("output_tokens", 0),
                        total_tokens=data.get("total_tokens", 0),
                        estimated_cost_usd=Decimal(
                            str(data.get("estimated_cost_usd", "0"))
                        ),
                    )
                connection.commit()
        except oracledb.Error as exc:
            raise OracleRepositoryError("AI usage insert failed") from exc


ai_usage_repository = AIUsageRepository()
