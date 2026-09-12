from __future__ import annotations

import importlib.util
from pathlib import Path


MIGRATION_PATH = (
    Path(__file__).resolve().parents[2]
    / "alembic"
    / "versions"
    / "20260912_document_prefix_index.py"
)


def _load_migration_module():
    assert MIGRATION_PATH.exists(), (
        "expected migration api/alembic/versions/"
        "20260912_document_prefix_index.py"
    )
    spec = importlib.util.spec_from_file_location(
        "document_prefix_index_migration",
        MIGRATION_PATH,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_document_prefix_index_migration_uses_safe_concurrent_ddl() -> None:
    module = _load_migration_module()
    source = MIGRATION_PATH.read_text()

    assert module.revision == "20260912_document_prefix_index"
    assert callable(module.upgrade)
    assert callable(module.downgrade)

    assert source.count("autocommit_block()") >= 2
    assert "SET lock_timeout" in source
    assert "SET statement_timeout" in source
    assert "RESET lock_timeout" in source
    assert "RESET statement_timeout" in source
    assert "CREATE INDEX CONCURRENTLY" in source
    assert "DROP INDEX CONCURRENTLY IF EXISTS ix_documents_table_id_id_c" in source
    assert "ix_documents_table_id_id_c" in source
    assert "ON documents (table_id, (id COLLATE \"C\"))" in source
