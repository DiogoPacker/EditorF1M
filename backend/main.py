from pathlib import Path
from contextlib import asynccontextmanager
import sqlite3
import asyncio

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from . import __version__

from .api.dependencies import store
from .domain.errors import RecordNotFound
from .api.routes import saves, drivers, teams, calendar, performance, parts, inspection, editor, management


@asynccontextmanager
async def lifespan(app):
    try:
        yield
    finally:
        store.close()


app = FastAPI(title="F1 Save Studio API", version=__version__, lifespan=lifespan, description="Editor local de F1 Manager 2024. GET consulta; PATCH edita a cópia; POST importa, desfaz e exporta. O original nunca é sobrescrito.")
# A single process is required. Serialize session requests, including exports,
# so a preview or read cannot observe half of another request's operation.
session_request_lock = asyncio.Lock()
for module in (saves, drivers, teams, calendar, performance, parts, inspection, editor, management):
    app.include_router(module.router)
STATIC = Path(__file__).resolve().parents[1] / "frontend"


@app.middleware("http")
async def local_origin(request: Request, call_next):
    if request.method not in ("GET", "HEAD", "OPTIONS"):
        origin = request.headers.get("origin")
        if origin and origin != str(request.base_url).rstrip("/"):
            return JSONResponse({"detail": "Origem não autorizada."}, status_code=403)
    if request.url.path.startswith('/api/saves/'):
        async with session_request_lock:
            response = await call_next(request)
    else:
        response = await call_next(request)
    response.headers['Cache-Control'] = 'no-store'
    return response


@app.exception_handler(ValueError)
async def invalid_value(request, error):
    return JSONResponse({"detail": str(error)}, status_code=422)


@app.exception_handler(RecordNotFound)
async def missing_record(request, error):
    return JSONResponse({"detail": str(error)}, status_code=404)


@app.exception_handler(sqlite3.Error)
async def invalid_database(request, error):
    return JSONResponse({"detail": f"Operação incompatível com este banco: {error}"}, status_code=422)



@app.get("/", include_in_schema=False)
def index():
    return FileResponse(STATIC / "index.html")

app.mount("/static", StaticFiles(directory=STATIC), name="static")
