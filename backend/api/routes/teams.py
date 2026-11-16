from fastapi import APIRouter
from ...application import services, editing
from ...models import TeamEdit
from ..dependencies import workspace
router = APIRouter()

@router.get("/api/saves/{identity}/teams", tags=["Equipes"])
def get_teams(identity: str):
    return services.teams(workspace(identity))


@router.patch("/api/saves/{identity}/teams/{team_id}", tags=["Equipes"])
def update_team(identity: str, team_id: int, edit: TeamEdit):
    return editing.update_team(workspace(identity), team_id, edit)
