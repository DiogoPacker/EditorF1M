from datetime import date

from . import services


def contracts(workspace, driver_id=None):
    query = "SELECT c.rowid AS contract_id,c.*,t.Formula,t.TeamName FROM Staff_Contracts c JOIN Staff_DriverData d USING(StaffID) JOIN Teams t USING(TeamID) WHERE c.ContractType IN(0,3)"
    return workspace.rows(query + (" AND c.StaffID=?" if driver_id is not None else "") + " ORDER BY c.ContractType DESC,t.Formula,c.PosInTeam", (driver_id,) if driver_id is not None else ())


def grid(workspace, year):
    if year not in (workspace.season, workspace.season + 1):
        raise ValueError("Selecione a temporada atual ou a próxima.")
    drivers = {row["StaffID"]: row for row in services.drivers(workspace)}
    all_contracts = contracts(workspace)
    future = {row["StaffID"]: row for row in all_contracts if row["ContractType"] == 3 and row["Formula"] == 1}
    result = []
    for team in services.teams(workspace):
        slots = []
        for seat in (1, 2):
            candidates = [row for row in all_contracts if row["TeamID"] == team["TeamID"] and row["PosInTeam"] == seat and row["EndSeason"] >= year and (row["ContractType"] == 0 if year == workspace.season else row["ContractType"] == 3 or row["StaffID"] not in future)]
            candidates.sort(key=lambda row: row["ContractType"], reverse=True)
            contract = candidates[0] if candidates else None
            driver = drivers.get(contract["StaffID"]) if contract else None
            slots.append({"seat": seat, "driver": driver, "contract": contract, "future": future.get(driver["StaffID"]) if driver else None, "conflict": len(candidates) > 1})
        academy_contracts = [row for row in all_contracts if row["TeamID"] == team["TeamID"] and row["PosInTeam"] > 2 and row["EndSeason"] >= year and (row["ContractType"] == 0 if year == workspace.season else row["ContractType"] == 3 or row["StaffID"] not in future)]
        academy = [{"driver": drivers[row["StaffID"]], "contract": row, "future": future.get(row["StaffID"])} for row in academy_contracts]
        reserves = [member["driver"] for member in academy]
        result.append({"team": team, "slots": slots, "reserves": reserves, "academy": academy})
    return {"year": year, "teams": result, "drivers": list(drivers.values())}


def transfer_preview(workspace, edit):
    drivers = {row["StaffID"]: row for row in services.drivers(workspace)}
    if edit.driver_id not in drivers or drivers[edit.driver_id]["Retired"]:
        raise ValueError("Selecione um piloto ativo.")
    year = workspace.season + (edit.timing == "next")
    target = next((row for row in grid(workspace, year)["teams"] if row["team"]["TeamID"] == edit.team_id), None)
    if not target:
        raise ValueError("Equipe de F1 não encontrada.")
    if edit.end_season < year:
        raise ValueError("O contrato precisa abranger a temporada de início.")
    slot = target["slots"][edit.seat - 1]
    if slot["conflict"]:
        raise ValueError("Existem contratos conflitantes nesta vaga. Resolva os contratos futuros antes de transferir.")
    outgoing = slot["driver"]
    if outgoing and outgoing["StaffID"] == edit.driver_id:
        raise ValueError("O piloto já ocupa esta vaga.")
    origin = next((row for row in contracts(workspace, edit.driver_id) if row["ContractType"] == 0 and row["PosInTeam"] in (1, 2)), None)
    if edit.timing == "next" and edit.displaced != "release":
        raise ValueError("Para contrato futuro, quem sai fica sem esta vaga na próxima temporada.")
    if outgoing and edit.displaced == "swap" and (not origin or (origin["TeamID"] == edit.team_id and origin["PosInTeam"] == edit.seat)):
        raise ValueError("Uma troca exige que o piloto de entrada tenha outra vaga de corrida.")
    return {"incoming": drivers[edit.driver_id], "outgoing": outgoing, "outgoing_contract": slot["contract"], "team": target["team"], "seat": edit.seat, "year": year, "origin": origin, "displaced": edit.displaced, "timing": edit.timing, "message": "Resultados e pontos anteriores são preservados. Contratos futuros já existentes dos envolvidos serão substituídos quando necessário."}


def _insert_contract(workspace, driver_id, team_id, seat, start_day, end_season, salary, contract_type=0, dual_role=False):
    workspace.db.execute("INSERT INTO Staff_Contracts(StaffID,ContractType,TeamID,PosInTeam,StartDay,EndSeason,Salary,StartingBonus,RaceBonus,RaceBonusTargetPos,BreakoutClause,AffiliateDualRoleClause) VALUES(?,?,?,?,?,?,?,0,0,1,0.5,?)", (driver_id, contract_type, team_id, seat, start_day, end_season, salary, int(dual_role)))
    if not workspace.scalar("SELECT COUNT(*) FROM Staff_Contracts WHERE StaffID=? AND TeamID=? AND PosInTeam=? AND ContractType=?", (driver_id, team_id, seat, contract_type)):
        raise ValueError("As regras deste save impediram a contratação (a equipe pode estar desativada pelo mod).")


def _close_contracts(workspace, driver_id, day):
    for contract in contracts(workspace, driver_id):
        if contract["ContractType"] == 0:
            workspace.db.execute("INSERT OR IGNORE INTO Staff_CareerHistory(StaffID,TeamID,StartDay,EndDay,PosInTeam) VALUES(?,?,?,?,?)", (driver_id, contract["TeamID"], contract["StartDay"], max(contract["StartDay"], day - 1), contract["PosInTeam"]))
    workspace.db.execute("DELETE FROM Staff_Contracts WHERE StaffID=? AND ContractType IN(0,1,2,3)", (driver_id,))
    workspace.db.execute("DELETE FROM Staff_ContractOffers WHERE StaffID=?", (driver_id,))
    workspace.db.execute("UPDATE Staff_DriverData SET AssignedCarNumber=NULL,FeederSeriesAssignedCarNumber=NULL WHERE StaffID=?", (driver_id,))
    workspace.db.execute("UPDATE Staff_RaceEngineerDriverAssignments SET IsCurrentAssignment=0 WHERE DriverID=?", (driver_id,))


def _assign_driver(workspace, driver_id, team_id, seat):
    formula = workspace.scalar("SELECT Formula FROM Teams WHERE TeamID=?", (team_id,))
    if seat in (1, 2) and formula in (1, 2, 3):
        position = (workspace.scalar("SELECT MAX(Position) FROM Races_DriverStandings WHERE SeasonID=? AND RaceFormula=?", (workspace.season, formula)) or 0) + 1
        workspace.db.execute("INSERT OR IGNORE INTO Races_DriverStandings(SeasonID,DriverID,Points,Position,LastPointsChange,LastPositionChange,RaceFormula) VALUES(?,?,0,?,0,0,?)", (workspace.season, driver_id, position, formula))
    if formula == 1 and seat in (1, 2):
        workspace.db.execute("UPDATE Staff_DriverData SET AssignedCarNumber=?,HasSuperLicense=1,HasRacedEnoughToJoinF1=1 WHERE StaffID=?", (seat, driver_id))
        workspace.db.execute("UPDATE Staff_GameData SET BestTeamFormula=1,BestF1PosInTeamSinceGameStart=MIN(COALESCE(BestF1PosInTeamSinceGameStart,?),?) WHERE StaffID=?", (seat, seat, driver_id))
        engineers = workspace.rows("SELECT c.StaffID FROM Staff_Contracts c JOIN Staff_GameData g USING(StaffID) WHERE c.TeamID=? AND c.ContractType=0 AND c.PosInTeam=? AND g.StaffType=(SELECT StaffType FROM Staff_Enum_StaffType WHERE Name='RaceEngineer')", (team_id, seat))
        for engineer in engineers:
            workspace.db.execute("INSERT INTO Staff_RaceEngineerDriverAssignments(RaceEngineerID,DriverID,DaysTogether,RelationshipLevel,IsCurrentAssignment) VALUES(?,?,0,0,1) ON CONFLICT(DriverID,RaceEngineerID) DO UPDATE SET IsCurrentAssignment=1", (engineer["StaffID"], driver_id))
    elif formula in (2, 3):
        workspace.db.execute("UPDATE Staff_DriverData SET FeederSeriesAssignedCarNumber=? WHERE StaffID=?", (seat, driver_id))


def transfer(workspace, edit):
    preview = transfer_preview(workspace, edit)
    outgoing = preview["outgoing"]
    outgoing_id = outgoing["StaffID"] if outgoing else None
    if outgoing_id != edit.expected_outgoing:
        raise ValueError("A vaga mudou desde a prévia. Confira novamente quem sairá.")
    if workspace.scalar("SELECT COUNT(*) FROM Save_RaceSimCars WHERE Active=1"):
        raise ValueError("Use um save fora de uma sessão de pista para transferir pilotos.")
    def operation():
        day = workspace.scalar("SELECT Day FROM Player_State LIMIT 1")
        if edit.timing == "next":
            start = (date(workspace.season + 1, 1, 1) - date(1899, 12, 30)).days
            involved = [edit.driver_id] + ([outgoing_id] if outgoing_id else [])
            for driver_id in involved:
                workspace.db.execute("DELETE FROM Staff_Contracts WHERE StaffID=? AND ContractType=3", (driver_id,))
                workspace.db.execute("UPDATE Staff_Contracts SET EndSeason=MIN(EndSeason,?) WHERE StaffID=? AND ContractType=0 AND PosInTeam IN(1,2)", (workspace.season, driver_id))
            _insert_contract(workspace, edit.driver_id, edit.team_id, edit.seat, start, edit.end_season, edit.salary, 3)
        else:
            original_outgoing = preview["outgoing_contract"]
            origin = preview["origin"]
            _close_contracts(workspace, edit.driver_id, day)
            if outgoing_id:
                _close_contracts(workspace, outgoing_id, day)
                if edit.displaced != "release":
                    if edit.displaced == "swap":
                        target_team, target_seat = origin["TeamID"], origin["PosInTeam"]
                    else:
                        target_team = edit.team_id
                        target_seat = max(3, (workspace.scalar("SELECT MAX(PosInTeam)+1 FROM Staff_Contracts WHERE ContractType=0 AND TeamID=?", (target_team,)) or 3))
                    _insert_contract(workspace, outgoing_id, target_team, target_seat, day, original_outgoing["EndSeason"], original_outgoing["Salary"])
                    _assign_driver(workspace, outgoing_id, target_team, target_seat)
            _insert_contract(workspace, edit.driver_id, edit.team_id, edit.seat, day, edit.end_season, edit.salary)
            _assign_driver(workspace, edit.driver_id, edit.team_id, edit.seat)
            count = workspace.scalar("SELECT COUNT(*) FROM Staff_Contracts c JOIN Staff_DriverData d USING(StaffID) WHERE c.TeamID=? AND c.PosInTeam=? AND c.ContractType=0", (edit.team_id, edit.seat))
            if count != 1:
                raise ValueError("A transferência não deixou uma única pessoa nesta vaga.")
    workspace.change(f"{'Contrato futuro' if edit.timing == 'next' else 'Transferência'} · {preview['incoming']['name']} → {preview['team']['name']} / carro {edit.seat}", operation)
    return preview


def cancel_future(workspace, driver_id):
    if not workspace.scalar("SELECT COUNT(*) FROM Staff_Contracts WHERE StaffID=? AND ContractType=3", (driver_id,)):
        raise ValueError("O piloto não tem contrato futuro.")
    workspace.change(f"Contrato futuro cancelado · piloto #{driver_id}", lambda: workspace.db.execute("DELETE FROM Staff_Contracts WHERE StaffID=? AND ContractType=3", (driver_id,)))
    return {"ok": True, "note": "Contratos atuais não são prolongados automaticamente ao cancelar o futuro."}


def academy_add(workspace, team_id, edit):
    driver = next((row for row in services.drivers(workspace) if row["StaffID"] == edit.driver_id), None)
    if not driver or driver["Retired"]:
        raise ValueError("Selecione um piloto ativo.")
    team = next((row for row in services.teams(workspace) if row["TeamID"] == team_id), None)
    if not team:
        raise ValueError("Equipe de F1 não encontrada.")
    year = workspace.season + (edit.timing == "next")
    if edit.end_season < year:
        raise ValueError("O contrato precisa abranger a temporada de início.")
    if workspace.scalar("SELECT COUNT(*) FROM Save_RaceSimCars WHERE Active=1"):
        raise ValueError("Use um save fora de uma sessão de pista para alterar a academia.")
    contract_type = 3 if edit.timing == "next" else 0
    if workspace.scalar("SELECT COUNT(*) FROM Staff_Contracts WHERE StaffID=? AND TeamID=? AND PosInTeam>2 AND ContractType=?", (edit.driver_id, team_id, contract_type)):
        raise ValueError("O piloto já pertence à academia nesta temporada. Edite o contrato existente.")
    def operation():
        day = workspace.scalar("SELECT Day FROM Player_State LIMIT 1")
        start = (date(year, 1, 1) - date(1899, 12, 30)).days if contract_type == 3 else day
        for contract in contracts(workspace, edit.driver_id):
            remove = (contract["Formula"] == 1 and contract["ContractType"] == contract_type) or (contract["Formula"] in (2, 3) and contract["ContractType"] == contract_type and not edit.keep_feeder_seat)
            if not remove:
                continue
            if contract["ContractType"] == 0:
                workspace.db.execute("INSERT OR IGNORE INTO Staff_CareerHistory(StaffID,TeamID,StartDay,EndDay,PosInTeam) VALUES(?,?,?,?,?)", (edit.driver_id, contract["TeamID"], contract["StartDay"], max(contract["StartDay"], day - 1), contract["PosInTeam"]))
            workspace.db.execute("DELETE FROM Staff_Contracts WHERE rowid=?", (contract["contract_id"],))
        if contract_type == 3:
            workspace.db.execute("UPDATE Staff_Contracts SET EndSeason=MIN(EndSeason,?) WHERE StaffID=? AND ContractType=0 AND TeamID IN(SELECT TeamID FROM Teams WHERE Formula=1)", (workspace.season, edit.driver_id))
            if not edit.keep_feeder_seat:
                workspace.db.execute("UPDATE Staff_Contracts SET EndSeason=MIN(EndSeason,?) WHERE StaffID=? AND ContractType=0 AND TeamID IN(SELECT TeamID FROM Teams WHERE Formula IN(2,3))", (workspace.season, edit.driver_id))
        else:
            workspace.db.execute("UPDATE Staff_DriverData SET AssignedCarNumber=NULL WHERE StaffID=?", (edit.driver_id,))
            workspace.db.execute("UPDATE Staff_RaceEngineerDriverAssignments SET IsCurrentAssignment=0 WHERE DriverID=?", (edit.driver_id,))
            if not edit.keep_feeder_seat:
                workspace.db.execute("UPDATE Staff_DriverData SET FeederSeriesAssignedCarNumber=NULL WHERE StaffID=?", (edit.driver_id,))
        workspace.db.execute("DELETE FROM Staff_ContractOffers WHERE StaffID=? AND TeamID IN(SELECT TeamID FROM Teams WHERE Formula=1)", (edit.driver_id,))
        workspace.db.execute("DELETE FROM Staff_Contracts WHERE StaffID=? AND ContractType IN(1,2) AND TeamID IN(SELECT TeamID FROM Teams WHERE Formula=1)", (edit.driver_id,))
        seat = max(3, (workspace.scalar("SELECT MAX(c.PosInTeam)+1 FROM Staff_Contracts c JOIN Staff_DriverData d USING(StaffID) WHERE c.TeamID=? AND c.ContractType IN(0,3)", (team_id,)) or 3))
        dual_role = edit.keep_feeder_seat and bool(workspace.scalar("SELECT COUNT(*) FROM Staff_Contracts c JOIN Teams t USING(TeamID) WHERE c.StaffID=? AND c.ContractType IN(0,3) AND t.Formula IN(2,3)", (edit.driver_id,)))
        _insert_contract(workspace, edit.driver_id, team_id, seat, start, edit.end_season, edit.salary, contract_type, dual_role)
    workspace.change(f"Academia{' futura' if contract_type == 3 else ''} · {driver['name']} → {team['name']}", operation)
    return grid(workspace, year)


def academy_remove(workspace, team_id, driver_id, timing):
    if workspace.scalar("SELECT COUNT(*) FROM Save_RaceSimCars WHERE Active=1"):
        raise ValueError("Use um save fora de uma sessão de pista para alterar a academia.")
    contract_type = 3 if timing == "next" else 0
    candidates = workspace.rows("SELECT rowid AS contract_id,* FROM Staff_Contracts WHERE StaffID=? AND TeamID=? AND PosInTeam>2 AND (ContractType=? OR (?='next' AND ContractType=0 AND EndSeason>=?)) ORDER BY ContractType DESC", (driver_id, team_id, contract_type, timing, workspace.season + 1))
    if not candidates:
        raise ValueError("Vínculo de academia não encontrado nesta temporada.")
    contract = candidates[0]
    def operation():
        if timing == "next" and contract["ContractType"] == 0:
            workspace.db.execute("UPDATE Staff_Contracts SET EndSeason=? WHERE rowid=?", (workspace.season, contract["contract_id"]))
            return
        if contract_type == 0:
            day = workspace.scalar("SELECT Day FROM Player_State LIMIT 1")
            for existing in workspace.rows("SELECT * FROM Staff_Contracts WHERE StaffID=? AND TeamID=? AND PosInTeam>2 AND ContractType=0", (driver_id, team_id)):
                workspace.db.execute("INSERT OR IGNORE INTO Staff_CareerHistory(StaffID,TeamID,StartDay,EndDay,PosInTeam) VALUES(?,?,?,?,?)", (driver_id, team_id, existing["StartDay"], max(existing["StartDay"], day - 1), existing["PosInTeam"]))
        workspace.db.execute("DELETE FROM Staff_Contracts WHERE rowid=?", (contract["contract_id"],))
    workspace.change(f"Academia · piloto #{driver_id} desligado da equipe #{team_id}", operation)
    return {"ok": True, "note": "Vagas de F2/F3 e contratos de outras temporadas foram preservados."}


def release_seat(workspace, team_id, seat, expected_driver, timing):
    if workspace.scalar("SELECT COUNT(*) FROM Save_RaceSimCars WHERE Active=1"):
        raise ValueError("Use um save fora de uma sessão de pista para liberar uma vaga.")
    year = workspace.season + (timing == "next")
    team = next((team for team in grid(workspace, year)["teams"] if team["team"]["TeamID"] == team_id), None)
    if not team or seat not in (1, 2):
        raise ValueError("Vaga de F1 não encontrada.")
    slot = team["slots"][seat - 1]
    if slot["conflict"] or not slot["driver"] or slot["driver"]["StaffID"] != expected_driver:
        raise ValueError("A vaga mudou. Atualize o grid antes de liberar o piloto.")
    contract = slot["contract"]
    def operation():
        if timing == "next" and contract["ContractType"] == 0:
            workspace.db.execute("UPDATE Staff_Contracts SET EndSeason=? WHERE rowid=?", (workspace.season, contract["contract_id"]))
        else:
            if timing == "now":
                day = workspace.scalar("SELECT Day FROM Player_State LIMIT 1")
                workspace.db.execute("INSERT OR IGNORE INTO Staff_CareerHistory(StaffID,TeamID,StartDay,EndDay,PosInTeam) VALUES(?,?,?,?,?)", (expected_driver, team_id, contract["StartDay"], max(contract["StartDay"], day - 1), seat))
                workspace.db.execute("UPDATE Staff_DriverData SET AssignedCarNumber=NULL WHERE StaffID=?", (expected_driver,))
                workspace.db.execute("UPDATE Staff_RaceEngineerDriverAssignments SET IsCurrentAssignment=0 WHERE DriverID=?", (expected_driver,))
            workspace.db.execute("DELETE FROM Staff_Contracts WHERE rowid=?", (contract["contract_id"],))
        workspace.db.execute("DELETE FROM Staff_ContractOffers WHERE StaffID=? AND TeamID=?", (expected_driver, team_id))
    workspace.change(f"Vaga liberada · {slot['driver']['name']} / {team['team']['name']} / carro {seat} / {year}", operation)
    return {"ok": True}
