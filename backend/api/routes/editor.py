from fastapi import APIRouter

from ...application import car_editor, engines, records, roster, services
from ...models import AcademyEdit, EngineAllocation, EngineCreate, EngineEdit, FittedEdit, TransferEdit
from typing import Literal
from ..dependencies import workspace


router = APIRouter(prefix="/api/saves/{identity}")


@router.get("/grid", tags=["Grid e contratos"])
def grid(identity: str, year: int | None = None):
    current = workspace(identity)
    return roster.grid(current, year or current.season)


@router.post("/transfers/preview", tags=["Grid e contratos"])
def preview(identity: str, edit: TransferEdit):
    return roster.transfer_preview(workspace(identity), edit)


@router.post("/transfers", tags=["Grid e contratos"])
def transfer(identity: str, edit: TransferEdit):
    return roster.transfer(workspace(identity), edit)


@router.delete("/drivers/{driver_id}/future-contract", tags=["Grid e contratos"])
def cancel_future(identity: str, driver_id: int):
    return roster.cancel_future(workspace(identity), driver_id)


@router.get("/compare/drivers", tags=["Análises"])
def compare(identity: str, left: int, right: int):
    current = workspace(identity)
    return {"left": services.driver_detail(current, left), "right": services.driver_detail(current, right)}


@router.post("/teams/{team_id}/academy", tags=["Grid e contratos"])
def add_academy(identity: str, team_id: int, edit: AcademyEdit):
    return roster.academy_add(workspace(identity), team_id, edit)


@router.delete("/teams/{team_id}/academy/{driver_id}", tags=["Grid e contratos"])
def remove_academy(identity: str, team_id: int, driver_id: int, timing: Literal["now", "next"] = "now"):
    return roster.academy_remove(workspace(identity), team_id, driver_id, timing)


@router.delete("/teams/{team_id}/seats/{seat}", tags=["Grid e contratos"])
def release_seat(identity: str, team_id: int, seat: int, expected_driver: int, timing: Literal["now", "next"] = "now"):
    return roster.release_seat(workspace(identity), team_id, seat, expected_driver, timing)


@router.get("/engines", tags=["Motores"])
def engine_catalog(identity: str):
    return engines.catalog(workspace(identity))


@router.post("/engines", tags=["Motores"], status_code=201)
def create_engine(identity: str, edit: EngineCreate):
    return engines.create_engine(workspace(identity), edit)


@router.patch("/engines/{engine_id}", tags=["Motores"])
def edit_engine(identity: str, engine_id: int, edit: EngineEdit):
    return engines.edit_engine(workspace(identity), engine_id, edit)


@router.patch("/teams/{team_id}/engine", tags=["Motores"])
def assign_engine(identity: str, team_id: int, edit: EngineAllocation):
    return engines.assign_engine(workspace(identity), team_id, edit.engine_id)


@router.get("/records/seasons", tags=["Records Hub"])
def get_seasons(identity: str):
    return records.seasons(workspace(identity))


@router.get("/records", tags=["Records Hub"])
def get_records(identity: str, season: int | None = None):
    current = workspace(identity)
    return records.hub(current, season or current.season)


@router.get("/teams/{team_id}/fitted", tags=["Carro instalado"])
def get_fitted(identity: str, team_id: int, car: int = 1):
    if car not in (1, 2):
        raise ValueError("Selecione o carro 1 ou 2.")
    return car_editor.fitted(workspace(identity), team_id, car)


@router.patch("/teams/{team_id}/fitted", tags=["Carro instalado"])
def edit_fitted(identity: str, team_id: int, edit: FittedEdit, car: int = 1):
    if car not in (1, 2):
        raise ValueError("Selecione o carro 1 ou 2.")
    return car_editor.edit_fitted(workspace(identity), team_id, car, edit)
