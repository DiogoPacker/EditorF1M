from fastapi import APIRouter

from ..dependencies import workspace
from ...application import facilities, expertise, team_identity, team_comparison
from ...models import FacilityEdit, ExpertiseBatch, TeamIdentityEdit

router = APIRouter(prefix="/api/saves/{identity}")


@router.patch("/teams/{team_id}/identity", tags=["Equipes"])
def identity(identity: str, team_id: int, edit: TeamIdentityEdit):
    return team_identity.edit_identity(workspace(identity), team_id, edit)


@router.get("/teams/{team_id}/facilities", tags=["Instalações"])
def get_facilities(identity: str, team_id: int):
    return facilities.catalog(workspace(identity), team_id)


@router.patch("/teams/{team_id}/facilities/{building_type}", tags=["Instalações"])
def edit_facility(identity: str, team_id: int, building_type: int, edit: FacilityEdit):
    return facilities.edit_facility(workspace(identity), team_id, building_type, edit)


@router.get("/teams/{team_id}/expertise-parts", tags=["Carro"])
def get_expertise(identity: str, team_id: int):
    return expertise.catalog(workspace(identity), team_id)


@router.patch("/teams/{team_id}/expertise-parts/{part_type}", tags=["Carro"])
def edit_expertise(identity: str, team_id: int, part_type: int, edit: ExpertiseBatch):
    return expertise.edit_batch(workspace(identity), team_id, part_type, edit)


@router.get("/compare/teams", tags=["Análises"])
def compare_teams(identity: str, season: int | None = None, metric: str = "points"):
    current = workspace(identity)
    return team_comparison.compare(current, current.season if season is None else season, metric)
