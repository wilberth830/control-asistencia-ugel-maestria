from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCHEMA_FILE = ROOT / "database" / "01_schema" / "01_create_tables.sql"
INDEX_FILE = ROOT / "database" / "01_schema" / "02_create_indexes.sql"
SEED_FILE = ROOT / "database" / "02_seed" / "01_seed_demo.sql"

EXPECTED_TABLES = [
    "user_account",
    "institution",
    "staff_member",
    "staff_institution",
    "biometric_import",
    "biometric_mark",
    "inconsistency",
    "justification",
    "attendance_day",
    "audit_log",
    "ai_usage_log",
]

EXPECTED_STATEMENTS = [
    "CONSTRAINT ck_staff_member_dni_len CHECK (REGEXP_LIKE(dni, '^[0-9]{8}$'))",
    "CONSTRAINT uk_ad_staff_date_import UNIQUE (staff_member_id, attendance_date, biometric_import_id)",
    "CONSTRAINT ck_bi_status CHECK (status IN ('draft', 'confirmed', 'cancelled'))",
    "CONSTRAINT uk_institution_modular_code UNIQUE (modular_code)",
    "CREATE INDEX ix_biometric_import_status ON biometric_import (status, period_start)",
    "CREATE INDEX ix_attendance_day_import ON attendance_day (biometric_import_id, attendance_date)",
    "CREATE INDEX ix_audit_log_entity ON audit_log (entity_name, entity_id)",
    "CREATE INDEX ix_ai_usage_import ON ai_usage_log (biometric_import_id, created_at)",
    "CONSTRAINT fk_ai_usage_import FOREIGN KEY (biometric_import_id) REFERENCES biometric_import (id)",
    "MERGE INTO user_account target",
    "MERGE INTO institution target",
    "MERGE INTO staff_member target",
    "create_table_if_missing",
    "add_constraint_if_missing",
    "add_primary_key_if_missing",
    "create_index_if_missing",
]


def normalized(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def assert_contains(haystack: str, needle: str) -> None:
    if normalized(needle).lower() not in normalized(haystack).lower():
        raise AssertionError(f"Missing expected SQL fragment: {needle}")


def main() -> None:
    schema = SCHEMA_FILE.read_text(encoding="utf-8")
    indexes = INDEX_FILE.read_text(encoding="utf-8")
    seed = SEED_FILE.read_text(encoding="utf-8")
    combined = "\n".join([schema, indexes, seed])

    for table_name in EXPECTED_TABLES:
        assert_contains(schema, f"CREATE TABLE {table_name}")

    for statement in EXPECTED_STATEMENTS:
        assert_contains(combined, statement)

    if "REPLACE_WITH_REAL_BCRYPT_HASH" in seed:
        raise AssertionError("Demo seed still contains the bcrypt placeholder")

    demo_hash_match = re.search(r"\$2[aby]\$12\$[./A-Za-z0-9]{53}", seed)
    if not demo_hash_match:
        raise AssertionError("Demo user password_hash is not a bcrypt cost-12 hash")

    if re.search(r"VALUES\s*\([^;]+,\s*\(", seed, re.IGNORECASE | re.DOTALL):
        raise AssertionError("Seed uses multi-row VALUES syntax instead of Oracle-compatible MERGE/SELECT")

    print("P1 static database checks passed")


if __name__ == "__main__":
    main()
