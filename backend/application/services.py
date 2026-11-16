from datetime import date, timedelta
import re

from teams import identity


DRIVER_LABELS = {"Cornering": "Curvas", "Braking": "Frenagem", "Control": "Controle", "Smoothness": "Suavidade", "Adaptability": "Adaptação", "Overtaking": "Ultrapassagem", "Defence": "Defesa", "Accuracy": "Precisão", "Reactions": "Reação", "Composure": "Compostura"}
PART_LABELS = {0: "Motor", 1: "ERS", 2: "Câmbio", 3: "Chassi", 4: "Asa dianteira", 5: "Asa traseira", 6: "Sidepods", 7: "Assoalho", 8: "Suspensão"}
STAT_LABELS = {0: "Fluxo dianteiro", 1: "Ar sujo", 2: "Preservação dos pneus", 3: "DRS", 4: "Redução de arrasto", 5: "Refrigeração do motor", 6: "Eficiência de combustível", 7: "Downforce em baixa", 8: "Downforce em média", 9: "Downforce em alta", 10: "Potência", 13: "Fluxo central", 15: "Peso / durabilidade"}


def display_name(value):
    literal = re.fullmatch(r"\[STRING_LITERAL:Value=\|(.*)\|\]", value, re.DOTALL)
    if literal:
        return literal.group(1)
    if value.startswith("["):
        value = value.strip("[]").split("_")[-1]
    return re.sub(r"(?<=[a-z])(?=[A-Z])", " ", value)


def teams(workspace):
    rows = workspace.rows("SELECT t.*,b.Balance,s.Points,s.Position FROM Teams t LEFT JOIN Finance_TeamBalance b USING(TeamID) LEFT JOIN Races_TeamStandings s ON s.TeamID=t.TeamID AND s.SeasonID=? WHERE t.Formula=1 ORDER BY s.Position", (workspace.season,))
    for row in rows:
        row["name"], row["color"], row["code"] = identity(row["TeamID"], row["TeamName"], bool(row["IsCustomTeam"]))
    return rows


def drivers(workspace):
    team_map = {team["TeamID"]: team for team in teams(workspace)}
    rows = workspace.rows("SELECT b.StaffID,b.FirstName,b.LastName,b.DOB_ISO,d.Aggression,d.Marketability,d.Improvability,d.DriverCode,g.Retired FROM Staff_BasicData b JOIN Staff_DriverData d USING(StaffID) JOIN Staff_GameData g USING(StaffID) ORDER BY b.LastName")
    contracts = workspace.rows("SELECT c.rowid AS contract_id,c.*,t.Formula,t.TeamName FROM Staff_Contracts c JOIN Teams t USING(TeamID) WHERE c.ContractType=0 ORDER BY CASE WHEN c.PosInTeam IN(1,2) THEN 0 ELSE 1 END,t.Formula,c.PosInTeam")
    futures = workspace.rows("SELECT c.rowid AS contract_id,c.*,t.TeamName FROM Staff_Contracts c JOIN Teams t USING(TeamID) WHERE c.ContractType=3 ORDER BY c.StartDay")
    current = {}
    for contract in contracts:
        current.setdefault(contract["StaffID"], contract)
    averages = dict((row["StaffID"], round(row["average"], 1)) for row in workspace.rows("SELECT StaffID,AVG(Val) AS average FROM Staff_PerformanceStats GROUP BY StaffID"))
    for row in rows:
        row["first_name_display"] = display_name(row["FirstName"])
        row["last_name_display"] = display_name(row["LastName"])
        row["code_display"] = display_name(row["DriverCode"]).upper()
        row["name"] = row["first_name_display"] + " " + row["last_name_display"]
        row["contract"] = current.get(row["StaffID"])
        row["affiliations"] = [contract for contract in contracts if contract["StaffID"] == row["StaffID"]]
        row["future_contracts"] = [contract for contract in futures if contract["StaffID"] == row["StaffID"]]
        row["team"] = team_map.get(row["contract"]["TeamID"]) if row["contract"] else None
        row["average"] = averages.get(row["StaffID"])
    return rows


def driver_detail(workspace, driver_id):
    driver = next((row for row in drivers(workspace) if row["StaffID"] == driver_id), None)
    if not driver:
        raise ValueError("Piloto não encontrado.")
    driver["stats"] = workspace.rows("SELECT s.StatID,s.Val,s.Max,e.Name FROM Staff_PerformanceStats s JOIN Staff_Enum_PerformanceStatTypes e ON e.Value=s.StatID WHERE s.StaffID=? ORDER BY s.StatID", (driver_id,))
    for stat in driver["stats"]:
        stat["label"] = DRIVER_LABELS.get(stat["Name"], display_name(stat["Name"]))
    driver["results"] = workspace.rows("SELECT r.RaceID,t.Name,x.FinishingPos,x.StartingPos,x.Points,x.DNF FROM Races_Results x JOIN Races r USING(RaceID) JOIN Races_Tracks t USING(TrackID) WHERE x.DriverID=? AND x.Season=? ORDER BY r.Day", (driver_id, workspace.season))
    return driver


def edit_driver(workspace, driver_id, edit):
    detail = driver_detail(workspace, driver_id)
    allowed = {stat["StatID"]: stat["Max"] for stat in detail["stats"]}
    for stat_id, value in edit.stats.items():
        if stat_id not in allowed or not 0 <= value <= min(100, allowed[stat_id]):
            raise ValueError(f"Atributo {stat_id}: valor permitido entre 0 e {min(100, allowed.get(stat_id, 0))}.")
    def operation():
        for field, column in [("first_name", "FirstName"), ("last_name", "LastName")]:
            value = getattr(edit, field)
            if value is not None:
                if not value.strip():
                    raise ValueError("O nome não pode ficar vazio.")
                workspace.db.execute(f"UPDATE Staff_BasicData SET {column}=? WHERE StaffID=?", (value.strip(), driver_id))
        for field, column in [("aggression", "Aggression"), ("marketability", "Marketability"), ("growth", "Improvability")]:
            value = getattr(edit, field)
            if value is not None:
                workspace.db.execute(f"UPDATE Staff_DriverData SET {column}=? WHERE StaffID=?", (value, driver_id))
        for stat_id, value in edit.stats.items():
            workspace.db.execute("UPDATE Staff_PerformanceStats SET Val=? WHERE StaffID=? AND StatID=?", (value, driver_id, stat_id))
    workspace.change(f"Piloto: {detail['name']} · atributos e perfil", operation)
    return driver_detail(workspace, driver_id)


def calendar(workspace):
    rows = workspace.rows("SELECT r.*,t.Name AS track,t.Laps,t.TrackLength FROM Races r JOIN Races_Tracks t USING(TrackID) WHERE r.SeasonID=? ORDER BY r.Day,r.RaceID", (workspace.season,))
    for index, row in enumerate(rows):
        row["round"] = index + 1
        row["date"] = (date(1899, 12, 30) + timedelta(days=row["Day"])).isoformat()
        row["track"] = display_name(row["track"])
        row["completed"] = bool(workspace.scalar("SELECT COUNT(*) FROM Races_Results WHERE Season=? AND RaceID=?", (workspace.season, row["RaceID"])))
    return rows


def projects(workspace, team_id):
    rows = workspace.rows("SELECT p.*,d.TeamID,d.PartType,d.ValidFrom,d.DesignWork,d.DesignWorkMax,d.DesignCost,d.CFD,d.WindTunnelTime FROM Parts_Projects p JOIN Parts_Designs d USING(DesignID) WHERE d.TeamID=? ORDER BY p.ProjectID DESC", (team_id,))
    for row in rows:
        row["part"] = PART_LABELS.get(row["PartType"], str(row["PartType"]))
        row["kind"] = "Fabricação" if not row["NewDesign"] else "Pesquisa" if row["ValidFrom"] > workspace.season else "Desenvolvimento"
        row["progress"] = min(100, row["DesignWork"] / max(1, row["DesignWorkMax"]) * 100) if row["NewDesign"] else None
    return rows


def parts(workspace, team_id):
    rows = workspace.rows("SELECT d.* FROM Parts_Designs d WHERE TeamID=? AND PartType BETWEEN 3 AND 8 ORDER BY ValidFrom DESC,DesignID DESC", (team_id,))
    equipped = workspace.rows("SELECT DesignID,LoadoutID FROM Parts_CarLoadout WHERE TeamID=?", (team_id,))
    for row in rows:
        row["part"] = PART_LABELS[row["PartType"]]
        row["cars"] = [item["LoadoutID"] for item in equipped if item["DesignID"] == row["DesignID"]]
    return rows


def part_stats(workspace, design_id):
    rows = workspace.rows("SELECT s.*,e.Name,d.PartType FROM Parts_Designs_StatValues s JOIN Parts_Enum_Stats e ON e.Value=s.PartStat JOIN Parts_Designs d USING(DesignID) WHERE s.DesignID=? ORDER BY s.PartStat", (design_id,))
    if not rows:
        raise ValueError("Design não encontrado.")
    for row in rows:
        row["label"] = STAT_LABELS.get(row["PartStat"], display_name(row["Name"]))
    return rows


def unit_value(stat_id, value, part_type):
    if stat_id in (0, 1, 2, 3, 4, 5, 13):
        return value / 10
    if stat_id in (7, 8, 9):
        scale, offset = {7: (497.6, 1489.8), 8: (496.8, 2479.5), 9: (974.048, 6803.2614)}[stat_id]
        return (value + offset) / scale
    if stat_id == 15 and part_type in range(3, 9):
        low, high = {3: (3800, 6500), 4: (1250, 4000), 5: (1650, 4600), 6: (2750, 5500), 7: (2100, 5000), 8: (1700, 4100)}[part_type]
        return low + value / 1000 * (high - low)
    raise ValueError("Conversão não implementada para este atributo. Use uma peça aerodinâmica suportada.")


FACTORS = {
    0: {4: .4, 6: .2, 8: .4}, 1: {4: .4, 5: .4, 7: .2}, 2: {4: .4, 8: .6},
    3: {3: .25, 5: .75}, 4: {3: .2, 5: .3, 6: .2, 7: .2, 8: .1}, 5: {3: .4, 6: .6},
    7: {4: .2, 5: .2, 7: .3, 8: .3}, 8: {4: .2, 5: .2, 7: .5, 8: .1},
    9: {4: .2, 5: .2, 7: .5, 8: .1}, 13: {3: .6, 6: .4},
}
METRICS = {
    "overall": ("Índice geral estimado", "%", {}, 0, 100),
    "top_speed": ("Velocidade máxima", "km/h", {4: 1}, 313, 328),
    "low": ("Curvas baixas", "G", {0: .6, 7: 1, 16: .24}, 2, 3),
    "medium": ("Curvas médias", "G", {0: .4, 13: .4, 8: 1, 16: .27}, 3, 4),
    "high": ("Curvas altas", "G", {13: .6, 9: 1, 16: .24}, 4, 5.5),
    "dirty_air": ("Tolerância ao ar sujo", "%", {1: 1}, 0, 100),
    "tyres": ("Preservação dos pneus", "%", {2: 1}, 0, 100),
    "cooling": ("Refrigeração do motor", "%", {5: 1}, 0, 100),
    "drs": ("DRS", "%", {3: 1}, 0, 100),
}


def car_performance(workspace, team_id, car=1, day=None):
    season = workspace.season
    if day is None:
        loadout = workspace.rows("SELECT PartType,DesignID FROM Parts_CarLoadout WHERE TeamID=? AND LoadoutID=? AND PartType BETWEEN 3 AND 8", (team_id, car))
    else:
        loadout = workspace.rows("SELECT PartType,MAX(DesignID) AS DesignID FROM Parts_Designs WHERE TeamID=? AND ValidFrom=? AND PartType BETWEEN 3 AND 8 AND (DayCreated<0 OR (DayCompleted>0 AND DayCompleted<=?)) GROUP BY PartType", (team_id, season, day))
    missing = sorted(set(range(3, 9)) - {row["PartType"] for row in loadout})
    raw = {}
    for row in loadout:
        raw[row["PartType"]] = {stat["PartStat"]: stat["Value"] for stat in workspace.rows("SELECT PartStat,Value FROM Parts_Designs_StatValues WHERE DesignID=?", (row["DesignID"],))}
    if missing:
        return {"metrics": {}, "parts": loadout, "missing": missing, "method": "Peças incompletas; estimativa indisponível."}
    aggregated = {stat: sum(raw.get(part, {}).get(stat, 0) * weight for part, weight in factors.items()) for stat, factors in FACTORS.items()}
    aggregated[16] = (20000 - sum(raw.get(part, {}).get(15, 0) * factor for part, factor in {3: 5, 4: 2, 5: 3, 6: 5, 7: 4, 8: 1}.items())) / 20
    metrics = {}
    for key, (label, unit, contributors, low, high) in METRICS.items():
        if key == "overall":
            continue
        score = sum(aggregated.get(stat, 0) * weight for stat, weight in contributors.items()) / sum(contributors.values()) / 1000
        metrics[key] = {"label": label, "unit": unit, "value": round(low + score * (high - low), 3)}
    weights = {"top_speed": .15, "low": .2, "medium": .2, "high": .2, "dirty_air": .05, "tyres": .05, "cooling": .05, "drs": .1}
    overall = sum((metrics[key]["value"] - METRICS[key][3]) / (METRICS[key][4] - METRICS[key][3]) * weight * 100 for key, weight in weights.items())
    metrics["overall"] = {"label": "Índice geral estimado", "unit": "%", "value": round(overall, 3)}
    return {"metrics": metrics, "parts": loadout, "missing": [], "method": "Estimativa do editor a partir das peças instaladas. Não inclui desgaste, acerto, pneus, combustível ou efeitos de corrida. Regras Sector33 preservadas; equivalência com a tela do jogo ainda não validada."}


def progression(workspace):
    grid = teams(workspace)
    races = [row for row in calendar(workspace) if row["completed"]]
    points = {(row["RaceID"], row["TeamID"]): row["total"] for row in workspace.rows("SELECT RaceID,TeamID,SUM(Points) AS total FROM Races_Results WHERE Season=? GROUP BY RaceID,TeamID", (workspace.season,))}
    sprints = {(row["RaceID"], row["TeamID"]): row["total"] for row in workspace.rows("SELECT RaceID,TeamID,SUM(ChampionshipPoints) AS total FROM Races_SprintResults WHERE SeasonID=? AND RaceFormula=1 GROUP BY RaceID,TeamID", (workspace.season,))}
    series = []
    for team in grid:
        total = 0
        values = []
        for race in races:
            key = (race["RaceID"], team["TeamID"])
            total += points.get(key, 0) + sprints.get(key, 0)
            values.append(total)
        series.append({"id": team["TeamID"], "name": team["name"], "color": team["color"], "values": values})
    return {"labels": [race["track"] for race in races], "series": series, "note": "Pontos acumulados de GPs e sprints registrados no banco."}
