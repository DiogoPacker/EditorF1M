from fastapi import APIRouter
from ...application import services, editing
from ...models import ContractEdit, DriverEdit
from ..dependencies import workspace
router = APIRouter()

@router.get("/api/saves/{identity}/drivers", tags=["Pilotos"])
def get_drivers(identity: str):
    return services.drivers(workspace(identity))


@router.get("/api/saves/{identity}/drivers/{driver_id}", tags=["Pilotos"])
def get_driver(identity: str, driver_id: int):
    return services.driver_detail(workspace(identity), driver_id)


@router.patch("/api/saves/{identity}/drivers/{driver_id}", tags=["Pilotos"])
def update_driver(identity: str, driver_id: int, edit: DriverEdit):
    return editing.update_driver(workspace(identity), driver_id, edit)


@router.patch("/api/saves/{identity}/contracts/{contract_id}", tags=["Pilotos"])
def update_contract(identity: str, contract_id: int, edit: ContractEdit):
    return editing.update_contract(workspace(identity), contract_id, edit)
