from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CONFIG_FILE = ROOT / "database" / "00_configuracion" / "00_create_schema.sql"
TABLES_FILE = ROOT / "database" / "01_schema" / "01_create_tables.sql"
INDEXES_FILE = ROOT / "database" / "01_schema" / "02_create_indexes.sql"
SEED_FILE = ROOT / "database" / "02_seed" / "01_seed_demo.sql"
GITIGNORE_FILE = ROOT / ".gitignore"

EXPECTED_TABLES = [
    "USER_ACCOUNT",
    "INSTITUTION",
    "STAFF_MEMBER",
    "STAFF_INSTITUTION",
    "BIOMETRIC_IMPORT",
    "BIOMETRIC_MARK",
    "INCONSISTENCY",
    "JUSTIFICATION",
    "ATTENDANCE_DAY",
    "AUDIT_LOG",
]

EXPECTED_CONSTRAINTS = [
    "PK_USER_ACCOUNT",
    "UK_USER_ACCOUNT_USERNAME",
    "CK_USER_ACCOUNT_ACTIVE",
    "PK_INSTITUTION",
    "UK_INSTITUTION_MODULAR_CODE",
    "CK_INSTITUTION_ACTIVE",
    "PK_STAFF_MEMBER",
    "UK_STAFF_MEMBER_DNI",
    "CK_STAFF_MEMBER_ACTIVE",
    "CK_STAFF_MEMBER_DNI_LEN",
    "PK_STAFF_INSTITUTION",
    "FK_SI_STAFF",
    "FK_SI_INST",
    "CK_SI_ACTIVE",
    "PK_BIOMETRIC_IMPORT",
    "FK_BI_USER",
    "CK_BI_STATUS",
    "PK_BIOMETRIC_MARK",
    "FK_BM_STAFF",
    "FK_BM_IMPORT",
    "CK_BM_TYPE",
    "CK_BM_STATUS",
    "PK_INCONSISTENCY",
    "FK_INC_MARK",
    "CK_INC_STATUS",
    "PK_JUSTIFICATION",
    "FK_JUST_STAFF",
    "FK_JUST_USER",
    "CK_JUST_PAY",
    "CK_JUST_STATUS",
    "CK_JUST_DATES",
    "PK_ATTENDANCE_DAY",
    "FK_AD_STAFF",
    "FK_AD_IMPORT",
    "FK_AD_JUST",
    "UK_AD_STAFF_DATE_IMPORT",
    "CK_AD_LATE",
    "CK_AD_STATUS",
    "PK_AUDIT_LOG",
    "FK_AUDIT_USER",
]

EXPECTED_INDEXES = [
    "IX_STAFF_INSTITUTION_STAFF",
    "IX_STAFF_INSTITUTION_INST",
    "IX_BIOMETRIC_IMPORT_STATUS",
    "IX_BIOMETRIC_MARK_IMPORT",
    "IX_BIOMETRIC_MARK_STAFF",
    "IX_INCONSISTENCY_STATUS",
    "IX_JUSTIFICATION_STAFF",
    "IX_ATTENDANCE_DAY_DATE",
    "IX_ATTENDANCE_DAY_IMPORT",
    "IX_AUDIT_LOG_ENTITY",
]


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def normalized(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().upper()


def assert_contains(text: str, fragment: str) -> None:
    if normalized(fragment) not in normalized(text):
        raise AssertionError(f"Missing expected fragment: {fragment}")


def assert_not_contains(text: str, fragment: str) -> None:
    if fragment.upper() in text.upper():
        raise AssertionError(f"Forbidden fragment found: {fragment}")


def main() -> None:
    config = read(CONFIG_FILE)
    tables = read(TABLES_FILE)
    indexes = read(INDEXES_FILE)
    seed = read(SEED_FILE)
    gitignore = read(GITIGNORE_FILE)

    for sql_text in [config, tables, indexes, seed]:
        assert_contains(sql_text, "WHENEVER SQLERROR EXIT SQL.SQLCODE")
        assert_contains(sql_text, "SET SERVEROUTPUT ON")

    assert_contains(config, "ALTER SESSION SET CONTAINER = &&PDB_NAME")
    assert_contains(config, "FROM dba_users")
    assert_contains(config, "GRANT CREATE SESSION TO &&APP_USER")
    assert_contains(config, "GRANT CREATE TABLE TO &&APP_USER")
    assert_contains(config, "GRANT CREATE VIEW TO &&APP_USER")
    assert_contains(config, "GRANT CREATE SEQUENCE TO &&APP_USER")
    assert_contains(config, "GRANT CREATE PROCEDURE TO &&APP_USER")
    assert_contains(config, "GRANT CREATE TRIGGER TO &&APP_USER")
    assert_not_contains(config, "GRANT DBA")
    assert_not_contains(config, "Asistencia123")

    assert_contains(tables, "user_tables")
    assert_contains(tables, "user_constraints")
    assert_contains(tables, "create_table_if_missing")
    assert_contains(tables, "add_constraint_if_missing")
    assert_contains(tables, "add_primary_key_if_missing")
    assert_contains(tables, "primary_key_exists")
    assert_not_contains(tables, "WHEN OTHERS THEN NULL")
    for table_name in EXPECTED_TABLES:
        assert_contains(tables, f"create_table_if_missing('{table_name.lower()}'")
    for constraint_name in EXPECTED_CONSTRAINTS:
        assert_contains(tables, constraint_name)

    assert_contains(indexes, "user_indexes")
    assert_contains(indexes, "user_ind_columns")
    assert_contains(indexes, "equivalent_index_exists")
    for index_name in EXPECTED_INDEXES:
        assert_contains(indexes, index_name)

    assert_contains(seed, "MERGE INTO institution")
    assert_contains(seed, "MERGE INTO user_account")
    assert_contains(seed, "MERGE INTO staff_member")
    assert_contains(seed, "NOT EXISTS")
    assert_contains(seed, "COMMIT")
    assert_not_contains(seed, "REPLACE_WITH_REAL_BCRYPT_HASH")

    assert_contains(gitignore, "database/00_configuracion/00_parametros.local.bat")

    print("Idempotency static checks passed")


if __name__ == "__main__":
    main()
