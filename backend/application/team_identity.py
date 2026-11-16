import re

from ..infrastructure.schema import has_columns
from ..domain.errors import RecordNotFound


def describe(workspace, row):
    from .services import display_name

    literal = row.get("TeamNameLocKey", "") or ""
    raw_name = literal if literal.startswith("[STRING_LITERAL:Value=|") else row["TeamName"]
    name = display_name(raw_name) if raw_name.startswith("[") else raw_name
    color = "#aab7d0"
    editable_color = has_columns(workspace, "Teams_Colours", {"ColourID", "TeamID", "Colour"})
    if editable_color:
        value = workspace.scalar("SELECT Colour FROM Teams_Colours WHERE TeamID=? ORDER BY ColourID LIMIT 1", (row["TeamID"],))
        if value is not None:
            color = f"#{int(value) & 0xffffff:06x}"
    words = re.findall(r"[A-Za-zÀ-ÿ0-9]+", name)
    code = ("".join(word[0] for word in words) if len(words) > 1 else name[:3]).upper()[:4]
    return {"name": name, "color": color, "code": code, "color_editable": editable_color}


def edit_identity(workspace, team_id, edit):
    if not workspace.scalar("SELECT COUNT(*) FROM Teams WHERE TeamID=? AND Formula=1", (team_id,)):
        raise RecordNotFound("Equipe não encontrada.")
    if edit.color is not None and not has_columns(workspace, "Teams_Colours", {"ColourID", "TeamID", "Colour"}):
        raise ValueError("Este save não contém uma tabela de cores compatível.")
    name = edit.name.strip()
    if not name or "|" in name or "[" in name or "]" in name:
        raise ValueError("Informe um nome sem delimitadores de localização: [, ] ou |.")

    def operation():
        workspace.db.execute("UPDATE Teams SET TeamName=? WHERE TeamID=?", (name, team_id))
        if has_columns(workspace, "Teams", {"TeamNameLocKey"}):
            workspace.db.execute("UPDATE Teams SET TeamNameLocKey=? WHERE TeamID=?", (f"[STRING_LITERAL:Value=|{name}|]", team_id))
        if edit.color is not None:
            value = 0xff000000 | int(edit.color[1:], 16)
            color_id = workspace.scalar("SELECT MIN(ColourID) FROM Teams_Colours WHERE TeamID=?", (team_id,))
            if color_id is None:
                color_id = (workspace.scalar("SELECT MAX(ColourID) FROM Teams_Colours") or 0) + 1
                workspace.db.execute("INSERT INTO Teams_Colours(ColourID,TeamID,Colour) VALUES(?,?,?)", (color_id, team_id, value))
            else:
                workspace.db.execute("UPDATE Teams_Colours SET Colour=? WHERE ColourID=? AND TeamID=?", (value, color_id, team_id))
    workspace.change(f"Identidade da equipe #{team_id} · {name}", operation)
    from .services import teams
    return next(team for team in teams(workspace) if team["TeamID"] == team_id)
