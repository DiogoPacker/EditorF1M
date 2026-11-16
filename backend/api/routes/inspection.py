from fastapi import APIRouter, HTTPException
from ..dependencies import workspace
router = APIRouter()

@router.get("/api/saves/{identity}/tables", tags=["Banco"])
def tables(identity: str):
    return workspace(identity).rows("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")


@router.get("/api/saves/{identity}/tables/{name}", tags=["Banco"])
def table(identity: str, name: str, offset: int = 0):
    if offset < 0:
        raise ValueError("Offset deve ser positivo.")
    current = workspace(identity)
    if not current.scalar("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name=?", (name,)):
        raise HTTPException(404, "Tabela não encontrada.")
    quoted = '"' + name.replace('"', '""') + '"'
    rows = current.rows(f"SELECT * FROM {quoted} LIMIT 100 OFFSET ?", (offset,))
    clean = [{key: f"<BLOB {len(value)} bytes>" if isinstance(value, bytes) else value for key, value in row.items()} for row in rows]
    return {"rows": clean, "total": current.scalar(f"SELECT COUNT(*) FROM {quoted}"), "offset": offset}
