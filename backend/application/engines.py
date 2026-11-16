from . import services


ENGINE_FIELDS = {
    "power": (0, 10, 80, 50),
    "fuel": (0, 6, 50, 20),
    "durability": (0, 14, 60, 50),
    "ers": (1, 15, 50, 50),
    "gearbox": (2, 15, 50, 50),
}


def supported(workspace):
    return workspace.scalar("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name IN('Custom_Engines_List','Custom_Engines_Stats','Custom_Engine_Allocations')") == 3


def catalog(workspace):
    if not supported(workspace):
        return {"supported": False, "engines": [], "note": "Este save não contém o sistema de motores personalizados Sector33. A criação/edição está indisponível para não inventar estruturas que o jogo não interpreta."}
    grid = services.teams(workspace)
    profiles = workspace.rows("SELECT engineId,name FROM Custom_Engines_List ORDER BY engineId")
    for profile in profiles:
        engine_id = profile["engineId"]
        stats = workspace.rows("SELECT * FROM Custom_Engines_Stats WHERE engineId=?", (engine_id,))
        profile["values"] = {key: next((row["unitValue"] for row in stats if row["designId"] == engine_id + offset and row["partStat"] == stat), None) for key, (offset, stat, base, scale) in ENGINE_FIELDS.items()}
        allocated = {row["teamId"] for row in workspace.rows("SELECT teamId FROM Custom_Engine_Allocations WHERE engineId=?", (engine_id,))}
        profile["teams"] = [team for team in grid if team["TeamID"] in allocated]
    return {"supported": True, "engines": profiles, "note": "Perfis personalizados de unidade de potência: aplicam atributos aos designs das equipes vinculadas. A criação de perfil não adiciona uma nova marca nativa na interface do jogo; depende do suporte Sector33. Motor, ERS e câmbio permanecem com os mesmos itens e desgaste."}


def _sync_team(workspace, team_id, engine_id):
    stats = workspace.rows("SELECT * FROM Custom_Engines_Stats WHERE engineId=?", (engine_id,))
    if not stats:
        raise ValueError("Perfil de motor sem atributos.")
    for design in workspace.rows("SELECT DesignID,PartType FROM Parts_Designs WHERE TeamID=? AND PartType BETWEEN 0 AND 2", (team_id,)):
        for stat in stats:
            if stat["designId"] != engine_id + design["PartType"]:
                continue
            workspace.db.execute("UPDATE Parts_Designs_StatValues SET Value=?,UnitValue=? WHERE DesignID=? AND PartStat=?", (stat["Value"], stat["unitValue"], design["DesignID"], stat["partStat"]))


def edit_engine(workspace, engine_id, edit):
    if not supported(workspace) or not workspace.scalar("SELECT COUNT(*) FROM Custom_Engines_List WHERE engineId=?", (engine_id,)):
        raise ValueError("Perfil de motor não encontrado.")
    def operation():
        workspace.db.execute("UPDATE Custom_Engines_List SET name=? WHERE engineId=?", (edit.name.strip(), engine_id))
        for key, (offset, stat, base, scale) in ENGINE_FIELDS.items():
            unit = getattr(edit, key)
            workspace.db.execute("INSERT INTO Custom_Engines_Stats(engineId,designId,partStat,unitValue,Value) VALUES(?,?,?,?,?) ON CONFLICT(engineId,designId,partStat) DO UPDATE SET unitValue=excluded.unitValue,Value=excluded.Value", (engine_id, engine_id + offset, stat, unit, (unit - base) * scale))
        for team in workspace.rows("SELECT DISTINCT teamId FROM Custom_Engine_Allocations WHERE engineId=?", (engine_id,)):
            _sync_team(workspace, team["teamId"], engine_id)
    workspace.change(f"Motor · {edit.name} · atributos e equipes clientes sincronizados", operation)
    return next(profile for profile in catalog(workspace)["engines"] if profile["engineId"] == engine_id)


def create_engine(workspace, edit):
    profiles = catalog(workspace)
    source = next((profile for profile in profiles["engines"] if profile["engineId"] == edit.base_engine), None)
    if not source:
        raise ValueError("Selecione um perfil existente como base.")
    if not edit.name.strip():
        raise ValueError("Informe o nome do motor.")
    engine_id = max(profile["engineId"] + 3 for profile in profiles["engines"])
    def operation():
        workspace.db.execute("INSERT INTO Custom_Engines_List(engineId,name) VALUES(?,?)", (engine_id, edit.name.strip()))
        for stat in workspace.rows("SELECT * FROM Custom_Engines_Stats WHERE engineId=?", (edit.base_engine,)):
            offset = stat["designId"] - edit.base_engine
            workspace.db.execute("INSERT INTO Custom_Engines_Stats(engineId,designId,partStat,unitValue,Value) VALUES(?,?,?,?,?)", (engine_id, engine_id + offset, stat["partStat"], stat["unitValue"], stat["Value"]))
    workspace.change(f"Novo perfil de motor · {edit.name}", operation)
    return next(profile for profile in catalog(workspace)["engines"] if profile["engineId"] == engine_id)


def assign_engine(workspace, team_id, engine_id):
    if not any(team["TeamID"] == team_id for team in services.teams(workspace)):
        raise ValueError("Equipe de F1 não encontrada.")
    if not supported(workspace) or not workspace.scalar("SELECT COUNT(*) FROM Custom_Engines_List WHERE engineId=?", (engine_id,)):
        raise ValueError("Perfil de motor não encontrado.")
    if workspace.scalar("SELECT COUNT(*) FROM Save_RaceSimCars WHERE Active=1"):
        raise ValueError("Troque o fornecedor em um save fora da pista.")
    def operation():
        workspace.db.execute("DELETE FROM Custom_Engine_Allocations WHERE teamId=?", (team_id,))
        workspace.db.execute("INSERT INTO Custom_Engine_Allocations(teamId,engineId) VALUES(?,?)", (team_id, engine_id))
        native = workspace.scalar("SELECT Value FROM Parts_Enum_EngineManufacturers WHERE EngineDesignID=?", (engine_id,))
        if native:
            workspace.db.execute("UPDATE Parts_TeamHistory SET EngineManufacturer=? WHERE SeasonID=? AND TeamID=?", (native, workspace.season, team_id))
        _sync_team(workspace, team_id, engine_id)
    workspace.change(f"Fornecedor de motor · equipe #{team_id} → perfil #{engine_id}", operation)
    return {"ok": True}
