from fastapi import APIRouter
from ...application import services, editing
from ...models import CalendarEdit
from ..dependencies import workspace
router = APIRouter()

@router.get("/api/saves/{identity}/calendar", tags=["Calendário"])
def get_calendar(identity: str):
    return services.calendar(workspace(identity))


@router.patch("/api/saves/{identity}/calendar/{race_id}", tags=["Calendário"])
def update_calendar(identity: str, race_id: int, edit: CalendarEdit):
    return editing.update_calendar(workspace(identity), race_id, edit)
