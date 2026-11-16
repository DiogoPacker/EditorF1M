from fastapi import HTTPException

from ..infrastructure.workspace import WorkspaceStore


store = WorkspaceStore()


def workspace(identity):
    try:
        return store.get(identity)
    except KeyError:
        raise HTTPException(404, "Sessão não encontrada. Abra um save.")
