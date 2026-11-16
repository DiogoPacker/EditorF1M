from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
import threading
import uuid
import io
import zipfile

from .codec import SaveContainer


ROOT = Path(__file__).resolve().parents[2] / "work" / "sessions"
MAX_UNDO_STEPS = 20
MAX_UNDO_BYTES = 128 * 1024 * 1024
MAX_OPEN_SESSIONS = 8


@dataclass
class Workspace:
    identity: str
    filename: str
    container: SaveContainer
    db: sqlite3.Connection
    history: list = field(default_factory=list)
    snapshots: list = field(default_factory=list)
    lock: threading.RLock = field(default_factory=threading.RLock)

    def rows(self, sql, params=()):
        return [dict(row) for row in self.db.execute(sql, params)]

    def scalar(self, sql, params=()):
        row = self.db.execute(sql, params).fetchone()
        return row[0] if row else None

    @property
    def season(self):
        return self.scalar("SELECT CurrentSeason FROM Player_State LIMIT 1")

    def change(self, description, operation):
        with self.lock:
            before = self.db.serialize()
            previous_history = self.history.copy()
            previous_snapshots = self.snapshots.copy()
            try:
                with self.db:
                    result = operation()
                after = self.db.serialize()
                if after == before:
                    return result
                self.snapshots.append(before)
                self.history.append({"description": description, "time": datetime.now(timezone.utc).isoformat()})
                while self.snapshots and (len(self.snapshots) > MAX_UNDO_STEPS or sum(map(len, self.snapshots)) > MAX_UNDO_BYTES):
                    self.snapshots.pop(0)
                self.persist()
                return result
            except Exception:
                self.db.deserialize(before)
                self.history[:] = previous_history
                self.snapshots[:] = previous_snapshots
                raise

    def persist(self):
        folder = ROOT / self.identity
        folder.mkdir(parents=True, exist_ok=True)
        # One atomic checkpoint keeps the database and its history in sync.
        target = folder / "checkpoint.zip"
        temporary = target.with_suffix(".tmp")
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_STORED) as archive:
            archive.writestr("working.sqlite", self.db.serialize())
            archive.writestr("session.json", json.dumps({"filename": self.filename, "history": self.history}, ensure_ascii=False))
        temporary.write_bytes(buffer.getvalue())
        temporary.replace(target)

    def undo(self):
        with self.lock:
            if not self.snapshots:
                raise ValueError("Não há alterações para desfazer nesta execução.")
            before = self.db.serialize()
            history = self.history.copy()
            snapshots = self.snapshots.copy()
            try:
                self.db.deserialize(self.snapshots.pop())
                self.history.pop()
                self.persist()
            except Exception:
                self.db.deserialize(before)
                self.history[:] = history
                self.snapshots[:] = snapshots
                raise


class WorkspaceStore:
    def __init__(self):
        self.items = {}
        self.lock = threading.RLock()

    def create(self, filename, content):
        with self.lock:
            return self._create(filename, content)

    def _create(self, filename, content):
        with self.lock:
            if len(self.items) >= MAX_OPEN_SESSIONS:
                raise ValueError("Limite de sessões abertas atingido. Exporte e reinicie o editor para liberar memória.")
        container = SaveContainer.parse(content)
        connection = sqlite3.connect(":memory:", check_same_thread=False)
        connection.row_factory = sqlite3.Row
        try:
            connection.deserialize(container.database)
        except Exception:
            connection.close()
            raise
        identity = uuid.uuid4().hex
        workspace = Workspace(identity, Path(filename.replace("\\", "/")).name, container, connection)
        required = {"Player_State", "Staff_BasicData", "Parts_Designs"}
        available = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if not required <= available:
            connection.close()
            raise ValueError("Este banco não contém o esquema esperado do F1 Manager.")
        folder = ROOT / identity
        try:
            folder.mkdir(parents=True, exist_ok=True)
            (folder / "original.bin").write_bytes(content)
            workspace.persist()
        except Exception:
            connection.close()
            raise
        with self.lock:
            self.items[identity] = workspace
        return workspace

    def get(self, identity):
        if len(identity) != 32 or any(character not in "0123456789abcdef" for character in identity):
            raise KeyError(identity)
        with self.lock:
            if identity not in self.items:
                folder = ROOT / identity
                if len(self.items) >= MAX_OPEN_SESSIONS:
                    raise ValueError("Limite de sessões abertas atingido. Reinicie o editor.")
                checkpoint = folder / "checkpoint.zip"
                if not checkpoint.exists() and not (folder / "session.json").exists():
                    raise KeyError(identity)
                if checkpoint.exists():
                    with zipfile.ZipFile(checkpoint) as archive:
                        metadata = json.loads(archive.read("session.json"))
                        database = archive.read("working.sqlite")
                else:
                    metadata = json.loads((folder / "session.json").read_text(encoding="utf-8"))
                    database = (folder / "working.sqlite").read_bytes()
                container = SaveContainer.parse((folder / "original.bin").read_bytes())
                connection = sqlite3.connect(":memory:", check_same_thread=False)
                connection.row_factory = sqlite3.Row
                connection.deserialize(database)
                self.items[identity] = Workspace(identity, metadata["filename"], container, connection, metadata["history"])
            return self.items[identity]

    def close(self):
        """Release SQLite connections when the application shuts down."""
        with self.lock:
            for workspace in self.items.values():
                with workspace.lock:
                    workspace.db.close()
            self.items.clear()
