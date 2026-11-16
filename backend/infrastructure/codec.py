from dataclasses import dataclass
import hashlib
import sqlite3
import struct
import zlib


MAX_EXPANDED = 256 * 1024 * 1024


@dataclass
class SaveContainer:
    original: bytes
    database: bytes
    prefix: bytes = b""
    auxiliary: tuple[bytes, bytes] = (b"", b"")
    suffix: bytes = b""
    is_save: bool = False

    @classmethod
    def parse(cls, content):
        if content.startswith(b"SQLite format 3\0"):
            validate_database(content)
            return cls(content, content)
        if not content.startswith(b"GVAS"):
            raise ValueError("Arquivo não reconhecido. Selecione um .sav GVAS ou SQLite.")
        for offset in range(20, min(len(content) - 1, 1024 * 1024)):
            if content[offset] != 120 or content[offset + 1] not in (1, 94, 156, 218):
                continue
            compressed_size, primary_size, second_size, third_size = struct.unpack_from("<4I", content, offset - 16)
            if compressed_size != len(content[offset:offset + compressed_size]) or not primary_size or primary_size + second_size + third_size > MAX_EXPANDED:
                continue
            try:
                inflater = zlib.decompressobj()
                payload = inflater.decompress(content[offset:offset + compressed_size], MAX_EXPANDED + 1)
            except zlib.error:
                continue
            if not inflater.eof or inflater.unused_data or len(payload) != primary_size + second_size + third_size:
                continue
            primary = payload[:primary_size]
            if not primary.startswith(b"SQLite format 3\0"):
                continue
            validate_database(primary)
            return cls(content, primary, content[:offset - 16], (payload[primary_size:primary_size + second_size], payload[primary_size + second_size:]), content[offset + compressed_size:], True)
        raise ValueError("Contêiner não compatível: tamanhos e bloco SQLite não puderam ser validados.")

    def export(self, database):
        validate_database(database)
        if not self.is_save:
            return database
        payload = database + b"".join(self.auxiliary)
        compressed = zlib.compress(payload, level=9)
        result = self.prefix + struct.pack("<4I", len(compressed), len(database), *map(len, self.auxiliary)) + compressed + self.suffix
        check = self.parse(result)
        if check.database != database or check.auxiliary != self.auxiliary or check.prefix != self.prefix or check.suffix != self.suffix:
            raise ValueError("A validação do save exportado falhou.")
        return result

    @property
    def fingerprint(self):
        return hashlib.sha256(self.original).hexdigest()


def validate_database(payload):
    connection = sqlite3.connect(":memory:")
    try:
        connection.deserialize(payload)
        if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise ValueError("O SQLite não passou na verificação de integridade.")
    finally:
        connection.close()
