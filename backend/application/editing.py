"""Application use cases for validated field edits; no HTTP dependencies."""
from . import services
from ..models import CalendarEdit, ContractEdit, DriverEdit, ExpertiseEdit, PartEdit, TeamEdit
from ..domain.errors import RecordNotFound
from ..infrastructure.repositories.edits import EditRepository

def update_team(current, team_id: int, edit: TeamEdit):
    repository = EditRepository(current)
    if not repository.has_balance(team_id):
        raise RecordNotFound("Equipe sem registro financeiro.")
    current.change(f"Equipe #{team_id} · caixa para {edit.balance}", lambda: repository.set_balance(team_id, edit.balance))
    return {"ok": True}


def update_driver(current, driver_id: int, edit: DriverEdit):
    return services.edit_driver(current, driver_id, edit)


def update_contract(current, contract_id: int, edit: ContractEdit):
    repository = EditRepository(current)
    contract_type = repository.contract_type(contract_id)
    if contract_type is None:
        raise RecordNotFound("Contrato atual não encontrado.")
    if edit.end_season < current.season + (contract_type == 3):
        raise ValueError("O contrato não pode terminar antes da temporada atual.")
    current.change(f"Contrato #{contract_id} · salário, duração e bônus", lambda: repository.set_contract(contract_id, edit))
    return {"ok": True}


def update_calendar(current, race_id: int, edit: CalendarEdit):
    race = next((race for race in services.calendar(current) if race["RaceID"] == race_id), None)
    if race is None:
        raise RecordNotFound("Corrida não encontrada.")
    if race["completed"]:
        raise ValueError("A corrida já foi realizada; seu clima histórico não será alterado.")
    current.change(f"Calendário · {race['track']} · clima e temperatura", lambda: EditRepository(current).set_weather(race_id, edit.weather, edit.temperature))
    return {"ok": True}


def update_part(current, design_id: int, stat_id: int, edit: PartEdit):
    row = next((row for row in services.part_stats(current, design_id) if row["PartStat"] == stat_id), None)
    if row is None:
        raise RecordNotFound("Atributo não encontrado.")
    converted = services.unit_value(stat_id, edit.value, row["PartType"])
    current.change(f"Peça #{design_id} · {row['label']} para {edit.value}", lambda: EditRepository(current).set_part(design_id, stat_id, edit.value, converted))
    return services.part_stats(current, design_id)


def update_expertise(current, team_id: int, part_type: int, stat_id: int, edit: ExpertiseEdit):
    repository = EditRepository(current)
    if not repository.has_expertise(team_id, part_type, stat_id):
        raise RecordNotFound("Expertise não encontrada.")
    current.change(f"Expertise · equipe #{team_id} · peça {part_type} · atributo {stat_id}", lambda: repository.set_expertise(team_id, part_type, stat_id, edit))
    return {"ok": True}
