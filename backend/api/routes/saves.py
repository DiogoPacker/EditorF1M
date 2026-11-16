from pathlib import Path
from urllib.parse import quote
from fastapi import APIRouter, HTTPException, UploadFile
from fastapi.responses import Response
from starlette.concurrency import run_in_threadpool
from ..dependencies import store, workspace
from ... import __version__
router = APIRouter()

def status(current):
    return {"id": current.identity, "filename": current.filename, "season": current.season, "changes": current.history, "undo_available": bool(current.snapshots), "can_export_save": current.container.is_save, "sha256": current.container.fingerprint, "modded": bool(current.scalar("SELECT COUNT(*) FROM sqlite_master WHERE name='Custom_Save_Config'"))}


@router.get("/api/health", tags=["Sistema"])
def health():
    return {"status": "ok", "version": __version__}


@router.post("/api/saves", tags=["Save"], status_code=201)
async def upload(file: UploadFile):
    content = await file.read(64 * 1024 * 1024 + 1)
    if len(content) > 64 * 1024 * 1024:
        raise HTTPException(413, "Limite de upload: 64 MB.")
    current = await run_in_threadpool(store.create, file.filename or "save.sav", content)
    return status(current)


@router.get("/api/saves/{identity}", tags=["Save"])
def save_status(identity: str):
    return status(workspace(identity))


@router.post("/api/saves/{identity}/undo", tags=["Save"])
def undo(identity: str):
    current = workspace(identity)
    current.undo()
    return status(current)


@router.post("/api/saves/{identity}/export", tags=["Save"])
def export(identity: str, format: str = "sav"):
    current = workspace(identity)
    if format not in ("sav", "sqlite"):
        raise ValueError("Formato esperado: sav ou sqlite.")
    if format == "sav" and not current.container.is_save:
        raise ValueError("Um SQLite isolado não contém metadados suficientes para gerar .sav.")
    database = current.db.serialize()
    payload = current.container.export(database) if format == "sav" else database
    filename = Path(current.filename).stem + "_editado." + format
    return Response(payload, media_type="application/octet-stream", headers={"Content-Disposition": "attachment; filename*=UTF-8''" + quote(filename), "X-Save-Verification": "roundtrip-ok"})
