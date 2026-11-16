from fastapi import APIRouter
from ...application import services
from ..dependencies import workspace
router = APIRouter()

@router.get("/api/saves/{identity}/performance", tags=["Análises"])
def performance(identity: str, car: int = 1):
    if car not in (1, 2):
        raise ValueError("Selecione o carro 1 ou 2.")
    current = workspace(identity)
    return [{"team": team, **services.car_performance(current, team["TeamID"], car)} for team in services.teams(current)]


@router.get("/api/saves/{identity}/performance/history", tags=["Análises"])
def performance_history(identity: str, metric: str = "high"):
    if metric not in services.METRICS:
        raise ValueError("Métrica não reconhecida.")
    current = workspace(identity)
    races = services.calendar(current)
    series = []
    for team in services.teams(current):
        values = []
        for race in races:
            if not race["completed"]:
                values.append(None)
                continue
            performance = services.car_performance(current, team["TeamID"], day=race["Day"])
            values.append(performance["metrics"].get(metric, {}).get("value"))
        series.append({"id": team["TeamID"], "name": team["name"], "color": team["color"], "values": values})
    return {"labels": [race["track"] for race in races], "series": series, "current_index": max((index for index, race in enumerate(races) if race["completed"]), default=-1), "note": "Evolução estimada dos últimos designs concluídos antes de cada GP; não é histórico das peças efetivamente instaladas. Etapas futuras ficam sem valores."}


@router.get("/api/saves/{identity}/progression", tags=["Análises"])
def get_progression(identity: str):
    return services.progression(workspace(identity))
