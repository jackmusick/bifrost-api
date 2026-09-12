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


class RecordingAutocommitBlock:
    def __init__(self, calls: list[tuple[str, str | None]]) -> None:
        self.calls = calls

    def __enter__(self):
        self.calls.append(("autocommit_enter", None))
        return self

    def __exit__(self, exc_type, exc, traceback):
        self.calls.append(("autocommit_exit", None))
        return False


class RecordingContext:
    def __init__(self, calls: list[tuple[str, str | None]]) -> None:
        self.calls = calls

    def autocommit_block(self) -> RecordingAutocommitBlock:
        return RecordingAutocommitBlock(self.calls)


class RecordingOp:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str | None]] = []

    def get_context(self) -> RecordingContext:
        return RecordingContext(self.calls)

    def execute(self, sql: str) -> None:
        self.calls.append(("execute", sql))


def _execute_with_recording_op(module, direction: str) -> list[tuple[str, str | None]]:
    recording_op = RecordingOp()
    original_op = module.op
    module.op = recording_op
    try:
        getattr(module, direction)()
    finally:
        module.op = original_op
    return recording_op.calls


def _assert_autocommit_sql_sequence(
    calls: list[tuple[str, str | None]],
    *,
    ddl_fragment: str,
) -> None:
    assert calls[0] == ("autocommit_enter", None)
    assert calls[-1] == ("autocommit_exit", None)

    sql = [value for kind, value in calls if kind == "execute"]
    assert len(sql) == len(calls) - 2
    assert all(kind in {"autocommit_enter", "execute", "autocommit_exit"} for kind, _ in calls)

    assert "SET lock_timeout" in sql[0]
    assert "SET statement_timeout" in sql[1]
    assert ddl_fragment in sql[2]
    assert "ix_documents_table_id_id_c" in sql[2]
    assert "RESET statement_timeout" in sql[-2]
    assert "RESET lock_timeout" in sql[-1]

    enter_index = calls.index(("autocommit_enter", None))
    exit_index = calls.index(("autocommit_exit", None))
    ddl_index = calls.index(("execute", sql[2]))
    assert enter_index < ddl_index < exit_index


def test_document_prefix_index_migration_uses_safe_concurrent_ddl() -> None:
    module = _load_migration_module()

    assert module.revision == "20260912_document_prefix_index"
    assert callable(module.upgrade)
    assert callable(module.downgrade)

    upgrade_calls = _execute_with_recording_op(module, "upgrade")
    downgrade_calls = _execute_with_recording_op(module, "downgrade")

    _assert_autocommit_sql_sequence(
        upgrade_calls,
        ddl_fragment="CREATE INDEX CONCURRENTLY",
    )
    assert "ON documents" in upgrade_calls[3][1]
    assert 'id COLLATE "C"' in upgrade_calls[3][1]

    _assert_autocommit_sql_sequence(
        downgrade_calls,
        ddl_fragment="DROP INDEX CONCURRENTLY IF EXISTS ix_documents_table_id_id_c",
    )
