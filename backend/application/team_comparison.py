from . import services
from ..infrastructure.schema import has_columns


METRICS = {"points": "Pontos", "wins": "Vitórias", "podiums": "Pódios", "poles": "Poles", "dnfs": "Abandonos"}


def compare(workspace, season, metric):
    if metric not in METRICS:
        raise ValueError("Métrica de comparação inválida.")
    grid = services.teams(workspace)
    races = workspace.rows("SELECT r.RaceID,r.Day,t.Name FROM Races r JOIN Races_Tracks t USING(TrackID) WHERE r.SeasonID=? ORDER BY r.Day,r.RaceID", (season,))
    results = workspace.rows("SELECT * FROM Races_Results WHERE Season=?", (season,))
    sprint_ok = has_columns(workspace, "Races_SprintResults", {"SeasonID", "RaceID", "TeamID", "ChampionshipPoints", "RaceFormula"})
    sprints = workspace.rows("SELECT * FROM Races_SprintResults WHERE SeasonID=? AND RaceFormula=1", (season,)) if sprint_ok else []
    qualifying_ok = has_columns(workspace, "Races_QualifyingResults", {"SeasonID", "RaceID", "TeamID", "FinishingPos", "QualifyingStage", "SprintShootout", "RaceFormula"})
    qualifying = workspace.rows("SELECT * FROM Races_QualifyingResults WHERE SeasonID=? AND RaceFormula=1 AND SprintShootout=0", (season,)) if qualifying_ok else []
    stages = {race["RaceID"]: max((row["QualifyingStage"] for row in qualifying if row["RaceID"] == race["RaceID"]), default=None) for race in races}
    qualifying_final = [row for row in qualifying if row["QualifyingStage"] == stages.get(row["RaceID"])]
    completed = {row["RaceID"] for row in results}
    series, summary = [], []
    for team in grid:
        totals = {key: 0 for key in METRICS}
        values, race_positions, qualifying_positions = [], {}, {}
        for race in races:
            race_id = race["RaceID"]
            main = [row for row in results if row["RaceID"] == race_id and row["TeamID"] == team["TeamID"]]
            sprint = [row for row in sprints if row["RaceID"] == race_id and row["TeamID"] == team["TeamID"]]
            qual = [row for row in qualifying_final if row["RaceID"] == race_id and row["TeamID"] == team["TeamID"]]
            totals["points"] += sum(row["Points"] or 0 for row in main) + sum(row["ChampionshipPoints"] or 0 for row in sprint)
            totals["wins"] += sum(row["FinishingPos"] == 1 and not row["DNF"] for row in main)
            totals["podiums"] += sum(1 <= row["FinishingPos"] <= 3 and not row["DNF"] for row in main)
            totals["dnfs"] += sum(bool(row["DNF"]) for row in main)
            totals["poles"] += sum(row["FinishingPos"] == 1 for row in qual)
            classified = [row["FinishingPos"] for row in main if row["FinishingPos"] > 0 and not row["DNF"]]
            if main:
                race_positions[str(race_id)] = min(classified) if classified else 10000
            # Earlier Q stages are offset so Q3 always beats Q2, even though
            # FinishingPos can restart at 1 in each stage.
            team_qual = [row for row in qualifying if row["RaceID"] == race_id and row["TeamID"] == team["TeamID"] and row["FinishingPos"] > 0]
            if team_qual:
                qualifying_positions[str(race_id)] = min((stages[race_id] - row["QualifyingStage"]) * 100 + row["FinishingPos"] for row in team_qual)
            has_data = race_id in completed or (metric == "points" and any(row["RaceID"] == race_id for row in sprints))
            values.append(totals[metric] if has_data else None)
        series.append({"id": team["TeamID"], "name": team["name"], "color": team["color"], "values": values})
        summary.append({"team": team, **totals, "race_positions": race_positions, "qualifying_positions": qualifying_positions})
    seasons = [row["SeasonID"] for row in workspace.rows("SELECT DISTINCT SeasonID FROM Races ORDER BY SeasonID DESC")]
    return {"season": season, "seasons": seasons, "metric": metric, "metrics": METRICS, "labels": [services.display_name(race["Name"]) for race in races], "series": series, "summary": summary, "qualifying_supported": qualifying_ok, "sprints_supported": sprint_ok, "note": "Totais acumulados a partir dos resultados: pontos incluem sprints; vitórias, pódios e abandonos são dos GPs principais. Ajustes oficiais de pontuação podem diferir. Etapas sem resultados ficam vazias."}
