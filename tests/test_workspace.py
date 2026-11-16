import sqlite3
from pathlib import Path

import pytest

from backend.infrastructure import workspace as module


@pytest.fixture
def saved_workspace(tmp_path, monkeypatch):
    monkeypatch.setattr(module, "ROOT", tmp_path)
    connection = sqlite3.connect(":memory:")
    connection.executescript("CREATE TABLE Player_State(CurrentSeason INTEGER); INSERT INTO Player_State VALUES(2026); CREATE TABLE Staff_BasicData(id INTEGER); CREATE TABLE Parts_Designs(id INTEGER);")
    payload = connection.serialize()
    connection.close()
    store = module.WorkspaceStore()
    workspace = store.create("test.sqlite", payload)
    yield workspace, store
    store.close()


def change_season(workspace):
    workspace.change("Next season", lambda: workspace.db.execute("UPDATE Player_State SET CurrentSeason=2027"))


def test_failed_checkpoint_restores_database_history_and_undo(saved_workspace, monkeypatch):
    workspace, store = saved_workspace
    original = workspace.db.serialize()
    real_replace = Path.replace

    def fail_replace(path, target):
        if Path(target).name == "checkpoint.zip":
            raise OSError("disk full")
        return real_replace(path, target)

    monkeypatch.setattr(Path, "replace", fail_replace)
    with pytest.raises(OSError, match="disk full"):
        change_season(workspace)
    assert workspace.db.serialize() == original
    assert workspace.history == workspace.snapshots == []
    restored_store = module.WorkspaceStore()
    try:
        restored = restored_store.get(workspace.identity)
        assert restored.season == 2026
        assert restored.history == []
    finally:
        restored_store.close()


def test_failed_undo_preserves_edit_and_snapshot(saved_workspace, monkeypatch):
    workspace, _ = saved_workspace
    change_season(workspace)
    history, snapshots = workspace.history.copy(), workspace.snapshots.copy()
    monkeypatch.setattr(workspace, "persist", lambda: (_ for _ in ()).throw(OSError("disk full")))
    with pytest.raises(OSError):
        workspace.undo()
    assert workspace.season == 2027
    assert workspace.history == history
    assert workspace.snapshots == snapshots


def test_undo_is_bounded_and_checkpoint_can_be_reopened(saved_workspace, monkeypatch):
    workspace, _ = saved_workspace
    monkeypatch.setattr(module, "MAX_UNDO_STEPS", 2)
    for year in (2027, 2028, 2029):
        workspace.change(str(year), lambda year=year: workspace.db.execute("UPDATE Player_State SET CurrentSeason=?", (year,)))
    assert len(workspace.snapshots) == 2
    restored_store = module.WorkspaceStore()
    try:
        restored = restored_store.get(workspace.identity)
        assert restored.season == 2029
        assert len(restored.history) == 3
    finally:
        restored_store.close()
    workspace.undo()
    assert workspace.season == 2028


def test_session_limit_and_shutdown(saved_workspace, monkeypatch):
    workspace, store = saved_workspace
    monkeypatch.setattr(module, "MAX_OPEN_SESSIONS", 1)
    with pytest.raises(ValueError, match="Limite"):
        store.create("extra.sqlite", workspace.container.original)
    store.close()
    with pytest.raises(sqlite3.ProgrammingError):
        workspace.db.execute("SELECT 1")


def test_legacy_session_is_readable_and_migrates_on_edit(saved_workspace):
    import json

    workspace, store = saved_workspace
    folder = module.ROOT / workspace.identity
    (folder / "working.sqlite").write_bytes(workspace.db.serialize())
    (folder / "session.json").write_text(json.dumps({"filename": "legacy.sqlite", "history": []}), encoding="utf-8")
    (folder / "checkpoint.zip").unlink()
    restored_store = module.WorkspaceStore()
    try:
        restored = restored_store.get(workspace.identity)
        assert restored.season == 2026
        change_season(restored)
        assert (folder / "checkpoint.zip").exists()
    finally:
        restored_store.close()
