from . import services


TRACK_CODES = {"albertpark": "AUS", "bahrain": "BAH", "jeddah": "SAU", "shanghai": "CHI", "suzuka": "JAP", "miami": "MIA", "imola": "IMO", "monaco": "MON", "montreal": "CAN", "catalunya": "SPA", "barcelona": "SPA", "redbullring": "AUT", "spielberg": "AUT", "silverstone": "GBR", "hungaroring": "HUN", "spa": "BEL", "spafrancorchamps": "BEL", "zandvoort": "NED", "monza": "ITA", "baku": "AZE", "marinabay": "SGP", "singapore": "SGP", "austin": "USA", "cota": "USA", "mexico": "MEX", "mexicocity": "MEX", "interlagos": "BRA", "saopaulo": "BRA", "lasvegas": "VEG", "losail": "QAT", "lusail": "QAT", "yasmarina": "UAE", "abudhabi": "UAE"}


def seasons(workspace):
    return [row["season"] for row in workspace.rows("SELECT Season AS season FROM Races_Results UNION SELECT SeasonID FROM Races_SprintResults UNION SELECT SeasonID FROM Races_DriverStandings ORDER BY season DESC")]


def hub(workspace, season, formula=1):
    if formula != 1:
        raise ValueError("Este painel cobre os resultados de F1; outras categorias não são misturadas aos GPs.")
    grid = {team["TeamID"]: team for team in services.teams(workspace)}
    names = {driver["StaffID"]: driver for driver in services.drivers(workspace)}
    races = workspace.rows("SELECT r.RaceID,r.Day,r.TrackID,r.WeekendType,t.Name FROM Races r JOIN Races_Tracks t USING(TrackID) WHERE r.SeasonID=? ORDER BY r.Day,r.RaceID", (season,))
    main_results = workspace.rows("SELECT RaceID,DriverID,TeamID,FinishingPos,Points,DNF FROM Races_Results WHERE Season=?", (season,))
    sprint_results = workspace.rows("SELECT RaceID,DriverID,TeamID,FinishingPos,ChampionshipPoints AS Points,DNF FROM Races_SprintResults WHERE SeasonID=? AND RaceFormula=1", (season,))
    standings = {row["DriverID"]: row for row in workspace.rows("SELECT * FROM Races_DriverStandings WHERE SeasonID=? AND RaceFormula=1", (season,))}
    ids = set(standings) | {result["DriverID"] for result in main_results + sprint_results}
    positions = {(result["DriverID"], result["RaceID"]): result for result in main_results}
    sprints = {(result["DriverID"], result["RaceID"]): result for result in sprint_results}
    rows = []
    for driver_id in ids:
        driver = names.get(driver_id, {"name": f"Piloto #{driver_id}", "StaffID": driver_id})
        participated = [result for result in main_results + sprint_results if result["DriverID"] == driver_id]
        latest = max(participated, key=lambda result: next((race["Day"] for race in races if race["RaceID"] == result["RaceID"]), 0), default={})
        cells = [{"race": positions.get((driver_id, race["RaceID"])), "sprint": sprints.get((driver_id, race["RaceID"]))} for race in races]
        points = sum(result["Points"] for result in participated)
        main = [result for result in main_results if result["DriverID"] == driver_id]
        rows.append({"driver_id": driver_id, "name": driver["name"], "team": grid.get(latest.get("TeamID"), driver.get("team")), "position": standings.get(driver_id, {}).get("Position"), "points": standings.get(driver_id, {}).get("Points", points), "result_points": points, "wins": sum(result["FinishingPos"] == 1 for result in main), "podiums": sum(result["FinishingPos"] <= 3 for result in main), "dnfs": sum(bool(result["DNF"]) for result in main), "cells": cells})
    rows.sort(key=lambda row: (row["position"] if row["position"] else 999, -row["points"], row["name"]))
    for race in races:
        race["name"] = services.display_name(race["Name"])
        race["code"] = TRACK_CODES.get(race["Name"].lower().replace(" ", "").replace("-", ""), race["name"][:3].upper())
    return {"season": season, "races": races, "drivers": rows, "note": "Posições e pontos de GPs e sprints armazenados no save. Pontos oficiais podem incluir ajustes não representados nos resultados individuais. Equipe exibida: última equipe registrada nos resultados desta temporada."}
