import sqlite3
import struct
import zlib

import pytest

from backend.infrastructure.codec import SaveContainer


def payload():
    connection = sqlite3.connect(":memory:")
    connection.execute("CREATE TABLE example(value INTEGER)")
    connection.execute("INSERT INTO example VALUES(42)")
    return connection.serialize()


def test_roundtrip_preserves_metadata_auxiliary_and_suffix():
    database = payload()
    auxiliary = b"second database\x00" * 100
    compressed = zlib.compress(database + auxiliary)
    prefix = b"GVAS" + b"metadata" * 12 + b"\x00" * 4
    original = prefix + struct.pack("<4I", len(compressed), len(database), len(auxiliary), 0) + compressed + b"trailer"
    parsed = SaveContainer.parse(original)
    connection = sqlite3.connect(":memory:")
    connection.deserialize(parsed.database)
    connection.execute("UPDATE example SET value=91")
    connection.commit()
    result = SaveContainer.parse(parsed.export(connection.serialize()))
    assert result.prefix == prefix
    assert result.auxiliary == (auxiliary, b"")
    assert result.suffix == b"trailer"
    reopened = sqlite3.connect(":memory:")
    reopened.deserialize(result.database)
    assert reopened.execute("SELECT value FROM example").fetchone()[0] == 91


def test_plain_sqlite_roundtrip():
    database = payload()
    container = SaveContainer.parse(database)
    assert not container.is_save
    assert container.export(database) == database


@pytest.mark.parametrize("invalid", [b"", b"not-a-save", b"GVAS" + b"\x00" * 100, b"GVAS" + b"\x00" * 40 + zlib.compress(payload())])
def test_invalid_container_rejected(invalid):
    with pytest.raises(ValueError):
        SaveContainer.parse(invalid)
