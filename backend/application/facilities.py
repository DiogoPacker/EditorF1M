from ..infrastructure.schema import has_columns
from ..domain.errors import RecordNotFound


REQUIRED = {
    "Buildings": {"BuildingID", "Type", "Name", "UpgradeLevel", "RequiredType", "RequiredLevel"},
    "Buildings_HQ": {"TeamID", "BuildingID", "BuildingType", "DegradationValue", "BuildingState"},
}


def catalog(workspace, team_id):
    missing = [table for table, fields in REQUIRED.items() if not has_columns(workspace, table, fields)]
    if missing:
        return {"supported": False, "facilities": [], "note": "Esquema de instalações incompatível: " + ", ".join(missing)}
    rows = workspace.rows("SELECT h.*,b.Name,b.UpgradeLevel FROM Buildings_HQ h JOIN Buildings b USING(BuildingID) WHERE h.TeamID=? ORDER BY h.BuildingType", (team_id,))
    types = {row["Type"]: row for row in workspace.rows("SELECT * FROM Building_Enum_Types")} if has_columns(workspace, "Building_Enum_Types", {"Type", "Name"}) else {}
    for row in rows:
        row["name"] = types.get(row["BuildingType"], {}).get("Name", row["Name"])
        row["group"] = types.get(row["BuildingType"], {}).get("BuildingGroup")
        row["condition"] = round(row["DegradationValue"] * 100, 3)
        row["levels"] = workspace.rows("SELECT BuildingID,UpgradeLevel FROM Buildings WHERE Type=? ORDER BY UpgradeLevel", (row["BuildingType"],))
        row["editable"] = row["BuildingState"] == 2
    return {"supported": True, "facilities": rows, "note": "Níveis e conservação do save. A edição é direta, sem cobrar construção/reforma. Obras em andamento são preservadas e não podem ser editadas nesta tela."}


def edit_facility(workspace, team_id, building_type, edit):
    data = catalog(workspace, team_id)
    if not data["supported"]:
        raise ValueError(data["note"])
    current = next((item for item in data["facilities"] if item["BuildingType"] == building_type), None)
    if not current:
        raise RecordNotFound("Instalação não encontrada nesta equipe.")
    if not current["editable"]:
        raise ValueError("Instalação em construção/reforma. Termine a obra no jogo antes de editar.")
    level = next((level for level in current["levels"] if level["BuildingID"] == edit.building_id), None)
    if not level:
        raise ValueError("O nível selecionado não pertence a esta instalação.")
    requirement = workspace.rows("SELECT RequiredType,RequiredLevel FROM Buildings WHERE BuildingID=?", (edit.building_id,))[0]
    if requirement["RequiredType"] is not None and requirement["RequiredLevel"]:
        available = workspace.scalar("SELECT b.UpgradeLevel FROM Buildings_HQ h JOIN Buildings b USING(BuildingID) WHERE h.TeamID=? AND h.BuildingType=?", (team_id, requirement["RequiredType"])) or 0
        if available < requirement["RequiredLevel"]:
            raise ValueError("O nível exige outra instalação com nível maior.")

    def operation():
        workspace.db.execute("UPDATE Buildings_HQ SET BuildingID=?,DegradationValue=? WHERE TeamID=? AND BuildingType=?", (edit.building_id, edit.condition / 100, team_id, building_type))
        if edit.building_id != current["BuildingID"] and has_columns(workspace, "Buildings_HQ_History", {"BuildingID", "Type", "TeamID", "DayConstructed"}):
            day = workspace.scalar("SELECT Day FROM Player_State LIMIT 1")
            workspace.db.execute("INSERT OR IGNORE INTO Buildings_HQ_History(BuildingID,Type,TeamID,DayConstructed) VALUES(?,?,?,?)", (edit.building_id, building_type, team_id, day))
    workspace.change(f"Instalações · equipe #{team_id} · {current['name']} · nível {level['UpgradeLevel']}", operation)
    return catalog(workspace, team_id)
