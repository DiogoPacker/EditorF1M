from fastapi import APIRouter
from ...application import services, editing
from ...models import ExpertiseEdit, PartEdit
from ..dependencies import workspace
router = APIRouter()

@router.get("/api/saves/{identity}/teams/{team_id}/projects", tags=["Carro"])
def get_projects(identity: str, team_id: int):
    return services.projects(workspace(identity), team_id)


@router.get("/api/saves/{identity}/teams/{team_id}/parts", tags=["Carro"])
def get_parts(identity: str, team_id: int):
    return services.parts(workspace(identity), team_id)


@router.get("/api/saves/{identity}/parts/{design_id}", tags=["Carro"])
def get_part(identity: str, design_id: int):
    return services.part_stats(workspace(identity), design_id)


@router.patch("/api/saves/{identity}/parts/{design_id}/{stat_id}", tags=["Carro"])
def update_part(identity: str, design_id: int, stat_id: int, edit: PartEdit):
    return editing.update_part(workspace(identity), design_id, stat_id, edit)


@router.get("/api/saves/{identity}/teams/{team_id}/expertise", tags=["Carro"])
def expertise(identity: str, team_id: int):
    current = workspace(identity)
    rows = current.rows("SELECT e.*,s.Name FROM Parts_TeamExpertise e JOIN Parts_Enum_Stats s ON s.Value=e.PartStat WHERE e.TeamID=? AND e.PartType BETWEEN 3 AND 8 ORDER BY e.PartType,e.PartStat", (team_id,))
    for row in rows:
        row["part"] = services.PART_LABELS[row["PartType"]]
        row["label"] = services.STAT_LABELS.get(row["PartStat"], row["Name"])
    return rows


@router.patch("/api/saves/{identity}/teams/{team_id}/expertise/{part_type}/{stat_id}", tags=["Carro"])
def update_expertise(identity: str, team_id: int, part_type: int, stat_id: int, edit: ExpertiseEdit):
    return editing.update_expertise(workspace(identity), team_id, part_type, stat_id, edit)
