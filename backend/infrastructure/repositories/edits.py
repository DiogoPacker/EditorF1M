"""SQL for editable records. Transactions are owned by Workspace.change."""


class EditRepository:
    def __init__(self, workspace):
        self.workspace = workspace

    def has_balance(self, team_id):
        return bool(self.workspace.scalar("SELECT COUNT(*) FROM Finance_TeamBalance WHERE TeamID=?", (team_id,)))

    def set_balance(self, team_id, balance):
        self.workspace.db.execute("UPDATE Finance_TeamBalance SET Balance=? WHERE TeamID=?", (balance, team_id))

    def contract_type(self, contract_id):
        return self.workspace.scalar("SELECT ContractType FROM Staff_Contracts WHERE rowid=? AND ContractType IN(0,3)", (contract_id,))

    def set_contract(self, contract_id, edit):
        self.workspace.db.execute("UPDATE Staff_Contracts SET Salary=?,EndSeason=?,RaceBonus=? WHERE rowid=?", (edit.salary, edit.end_season, edit.race_bonus, contract_id))

    def set_weather(self, race_id, weather, temperature):
        self.workspace.db.execute("UPDATE Races SET RainRace=?,WeatherStateRace=?,TemperatureRace=? WHERE RaceID=?", (int(weather >= 8), weather, temperature, race_id))

    def set_part(self, design_id, stat_id, value, converted):
        self.workspace.db.execute("UPDATE Parts_Designs_StatValues SET Value=?,UnitValue=? WHERE DesignID=? AND PartStat=?", (value, converted, design_id, stat_id))

    def has_expertise(self, team_id, part_type, stat_id):
        return bool(self.workspace.scalar("SELECT COUNT(*) FROM Parts_TeamExpertise WHERE TeamID=? AND PartType=? AND PartStat=?", (team_id, part_type, stat_id)))

    def set_expertise(self, team_id, part_type, stat_id, edit):
        self.workspace.db.execute("UPDATE Parts_TeamExpertise SET Expertise=?,NextSeasonExpertise=? WHERE TeamID=? AND PartType=? AND PartStat=?", (edit.expertise, edit.next_season, team_id, part_type, stat_id))
