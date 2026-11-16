from . import services
from ..infrastructure.schema import has_columns


ENGINE_FIELDS = {
    "power": (0, 10, 80, 50),
    "fuel": (0, 6, 50, 20),
    "durability": (0, 14, 60, 50),
    "ers": (1, 15, 50, 50),
    "gearbox": (2, 15, 50, 50),
}


def supported(workspace):
    return all(has_columns(workspace, table, fields) for table, fields in {
        'Custom_Engines_List': {'engineId', 'name'},
        'Custom_Engines_Stats': {'engineId', 'designId', 'partStat', 'unitValue', 'Value'},
        'Custom_Engine_Allocations': {'teamId', 'engineId'},
    }.items())


def native_catalog(workspace):
    if not has_columns(workspace, 'Parts_Enum_EngineManufacturers', {'Value', 'Name', 'EngineDesignID', 'ErsDesignID', 'GearboxDesignID'}):
        return {'supported': False, 'create_supported': False, 'allocation_supported': False, 'engines': [], 'note': 'Não há esquema de motores reconhecido neste save.'}
    grid = services.teams(workspace)
    profiles = []
    for row in workspace.rows('SELECT * FROM Parts_Enum_EngineManufacturers ORDER BY Value'):
        values = {}
        designs = [row['EngineDesignID'], row['ErsDesignID'], row['GearboxDesignID']]
        for key, (offset, stat, _, _) in ENGINE_FIELDS.items():
            values[key] = workspace.scalar('SELECT UnitValue FROM Parts_Designs_StatValues WHERE DesignID=? AND PartStat=?', (designs[offset], stat))
        customers = set()
        if has_columns(workspace, 'Parts_TeamHistory', {'TeamID', 'SeasonID', 'EngineManufacturer'}):
            customers = {item['TeamID'] for item in workspace.rows('SELECT TeamID FROM Parts_TeamHistory WHERE SeasonID=? AND EngineManufacturer=?', (workspace.season, row['Value']))}
        profiles.append({'engineId': row['Value'], 'name': row['Name'], 'values': values, 'teams': [team for team in grid if team['TeamID'] in customers]})
    return {'supported': True, 'mode': 'native', 'create_supported': False, 'allocation_supported': False, 'engines': profiles, 'note': 'Fornecedores nativos do save. Edição dos designs de referência e das equipes clientes; criação de marca e troca de fornecedor não estão disponíveis neste esquema. Recursos dependem das tabelas e regras do arquivo importado.'}


def catalog(workspace):
    if not supported(workspace):
        return native_catalog(workspace)
    grid = services.teams(workspace)
    profiles = workspace.rows("SELECT engineId,name FROM Custom_Engines_List ORDER BY engineId")
    for profile in profiles:
        engine_id = profile["engineId"]
        stats = workspace.rows("SELECT * FROM Custom_Engines_Stats WHERE engineId=?", (engine_id,))
        profile["values"] = {key: next((row["unitValue"] for row in stats if row["designId"] == engine_id + offset and row["partStat"] == stat), None) for key, (offset, stat, base, scale) in ENGINE_FIELDS.items()}
        allocated = {row["teamId"] for row in workspace.rows("SELECT teamId FROM Custom_Engine_Allocations WHERE engineId=?", (engine_id,))}
        profile["teams"] = [team for team in grid if team["TeamID"] in allocated]
    return {"supported": True, "create_supported": True, "allocation_supported": True, "mode": "profiles", "engines": profiles, "note": "Perfis de unidade de potência encontrados no save. Aplicam atributos aos designs das equipes vinculadas; não criam novas marcas nativas. Itens e desgaste são preservados."}


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
    if not supported(workspace):
        return edit_native(workspace, engine_id, edit)
    if not supported(workspace) or not workspace.scalar("SELECT COUNT(*) FROM Custom_Engines_List WHERE engineId=?", (engine_id,)):
        raise ValueError("Perfil de motor não encontrado.")
    def operation():
        workspace.db.execute("UPDATE Custom_Engines_List SET name=? WHERE engineId=?", (edit.name.strip(), engine_id))
        for key, (offset, stat, base, scale) in ENGINE_FIELDS.items():
            unit = getattr(edit, key)
            if unit is None:
                continue
            workspace.db.execute("INSERT INTO Custom_Engines_Stats(engineId,designId,partStat,unitValue,Value) VALUES(?,?,?,?,?) ON CONFLICT(engineId,designId,partStat) DO UPDATE SET unitValue=excluded.unitValue,Value=excluded.Value", (engine_id, engine_id + offset, stat, unit, (unit - base) * scale))
        for team in workspace.rows("SELECT DISTINCT teamId FROM Custom_Engine_Allocations WHERE engineId=?", (engine_id,)):
            _sync_team(workspace, team["teamId"], engine_id)
    workspace.change(f"Motor · {edit.name} · atributos e equipes clientes sincronizados", operation)
    return next(profile for profile in catalog(workspace)["engines"] if profile["engineId"] == engine_id)


def edit_native(workspace, engine_id, edit):
    profile = next((item for item in native_catalog(workspace)['engines'] if item['engineId'] == engine_id), None)
    if not profile:
        raise ValueError('Fornecedor nativo não encontrado.')
    manufacturer = workspace.rows('SELECT * FROM Parts_Enum_EngineManufacturers WHERE Value=?', (engine_id,))[0]
    templates = [manufacturer['EngineDesignID'], manufacturer['ErsDesignID'], manufacturer['GearboxDesignID']]
    def operation():
        workspace.db.execute('UPDATE Parts_Enum_EngineManufacturers SET Name=? WHERE Value=?', (edit.name.strip(), engine_id))
        for key, (offset, stat, _, scale) in ENGINE_FIELDS.items():
            value = getattr(edit, key)
            if value is None:
                continue
            original = workspace.rows('SELECT Value,UnitValue FROM Parts_Designs_StatValues WHERE DesignID=? AND PartStat=?', (templates[offset], stat))
            if not original:
                raise ValueError(f'Atributo {key} não disponível neste fornecedor.')
            raw = original[0]['Value'] + (value - original[0]['UnitValue']) * scale
            targets = {templates[offset]}
            for team in profile['teams']:
                targets.update(row['DesignID'] for row in workspace.rows('SELECT DesignID FROM Parts_Designs WHERE TeamID=? AND PartType=?', (team['TeamID'], offset)))
            for design in targets:
                workspace.db.execute('UPDATE Parts_Designs_StatValues SET Value=?,UnitValue=? WHERE DesignID=? AND PartStat=?', (raw, value, design, stat))
    workspace.change(f"Motor nativo · {edit.name}", operation)
    return next(item for item in native_catalog(workspace)['engines'] if item['engineId'] == engine_id)


def create_engine(workspace, edit):
    if not supported(workspace):
        raise ValueError("Este save permite editar fornecedores nativos, mas não criar novos perfis de motor.")
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
