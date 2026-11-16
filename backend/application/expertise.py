from ..infrastructure.schema import has_columns
from . import services


def catalog(workspace, team_id):
    if not has_columns(workspace, "Parts_TeamExpertise", {"TeamID", "PartType", "PartStat", "Expertise", "NextSeasonExpertise"}):
        return {"supported": False, "parts": [], "note": "Este save não contém expertise compatível."}
    rows = workspace.rows("SELECT * FROM Parts_TeamExpertise WHERE TeamID=? AND PartType BETWEEN 3 AND 8 ORDER BY PartType,PartStat", (team_id,))
    parts = []
    for part_type in sorted({row["PartType"] for row in rows}):
        stats = []
        for row in rows:
            if row["PartType"] == part_type:
                row.update(label=services.STAT_LABELS.get(row["PartStat"], f"Atributo {row['PartStat']}"), direction=-1 if row["PartStat"] == 15 else 1)
                stats.append(row)
        parts.append({"part_type": part_type, "name": services.PART_LABELS.get(part_type, str(part_type)), "stats": stats})
    return {"supported": True, "parts": parts, "note": "Expertise de desenvolvimento, não a peça instalada. + melhora e − piora em 10 pontos brutos por atributo; peso/durabilidade usa o sentido inverso para priorizar desempenho e pode reduzir a vida útil."}


def edit_batch(workspace, team_id, part_type, edit):
    part = next((part for part in catalog(workspace, team_id)["parts"] if part["part_type"] == part_type), None)
    if not part or not set(edit.stats) <= {row["PartStat"] for row in part["stats"]}:
        raise ValueError("Atributos não pertencem à expertise desta peça.")
    if any(not 0 <= value <= 1000 for value in edit.stats.values()):
        raise ValueError("Expertise deve ficar entre 0 e 1000.")
    column = "Expertise" if edit.target == "current" else "NextSeasonExpertise"
    def operation():
        for stat_id, value in edit.stats.items():
            workspace.db.execute(f"UPDATE Parts_TeamExpertise SET {column}=? WHERE TeamID=? AND PartType=? AND PartStat=?", (value, team_id, part_type, stat_id))
    workspace.change(f"Expertise · equipe #{team_id} · {part['name']} · {'temporada atual' if edit.target == 'current' else 'próxima temporada'}", operation)
    return catalog(workspace, team_id)
