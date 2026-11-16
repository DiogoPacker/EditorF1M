import hashlib
import sqlite3

from backend.infrastructure.codec import SaveContainer
from backend.main import app, store
from backend.infrastructure.workspace import WorkspaceStore


def test_health_and_static(client):
    assert client.get("/api/health").json()["status"] == "ok"
    assert client.get("/").status_code == 200
    assert client.get("/static/app.js").status_code == 200
    assert client.get("/openapi.json").status_code == 200


def test_missing_session_and_invalid_upload(client):
    assert client.get("/api/saves/invalid").status_code == 404
    assert client.post("/api/saves", files={"file": ("bad.sav", b"bad")}).status_code == 422


def test_cross_origin_mutation_rejected(client):
    assert client.post("/api/saves", headers={"Origin": "https://example.com"}, files={"file": ("bad.sav", b"bad")}).status_code == 403


def test_all_screens_queries(client, loaded):
    identity, original = loaded
    for path in ("", "/teams", "/drivers", "/drivers/1", "/calendar", "/teams/3/projects", "/teams/3/parts", "/performance", "/performance?car=2", "/performance/history", "/progression", "/teams/3/expertise", "/tables", "/tables/Player_State"):
        response = client.get(f"/api/saves/{identity}{path}")
        assert response.status_code == 200, (path, response.text)
    names = {team["name"] for team in client.get(f"/api/saves/{identity}/teams").json()}
    assert {"Alfa Romeo Racing", "AlphaTauri", "Cadillac"} <= names


def test_driver_edit_export_and_undo(client, loaded):
    identity, original = loaded
    prefix = f"/api/saves/{identity}"
    driver = client.get(prefix + "/drivers/1").json()
    stat = driver["stats"][0]
    value = max(0, stat["Val"] - 1)
    result = client.patch(prefix + "/drivers/1", json={"stats": {str(stat["StatID"]): value}})
    assert result.status_code == 200, result.text
    exported = client.post(prefix + "/export")
    assert exported.status_code == 200
    parsed = SaveContainer.parse(exported.content)
    source = SaveContainer.parse(original)
    assert source.auxiliary == parsed.auxiliary
    assert source.prefix == parsed.prefix
    connection = sqlite3.connect(":memory:")
    connection.deserialize(parsed.database)
    assert connection.execute("SELECT Val FROM Staff_PerformanceStats WHERE StaffID=1 AND StatID=?", (stat["StatID"],)).fetchone()[0] == value
    assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    assert client.post(prefix + "/undo").status_code == 200
    restored = client.get(prefix + "/drivers/1").json()
    assert restored["stats"] == driver["stats"]
    assert hashlib.sha256(store.get(identity).container.original).digest() == hashlib.sha256(original).digest()


def test_invalid_stats_are_atomic(client, loaded):
    identity, original = loaded
    prefix = f"/api/saves/{identity}"
    before = store.get(identity).db.serialize()
    response = client.patch(prefix + "/drivers/1", json={"first_name": "Changed", "stats": {"9999": 101}})
    assert response.status_code == 422
    assert store.get(identity).db.serialize() == before
    assert not client.get(prefix).json()["changes"]


def test_edit_finance_calendar_contract_and_part(client, loaded):
    identity, original = loaded
    prefix = f"/api/saves/{identity}"
    assert client.patch(prefix + "/teams/3", json={"balance": 12345678}).status_code == 200
    races = client.get(prefix + "/calendar").json()
    future = next(race for race in races if not race["completed"])
    past = next(race for race in races if race["completed"])
    assert client.patch(prefix + f"/calendar/{future['RaceID']}", json={"weather": 16, "temperature": 25}).status_code == 200
    updated = next(race for race in client.get(prefix + "/calendar").json() if race["RaceID"] == future["RaceID"])
    assert updated["RainRace"] == 1 and updated["WeatherStateRace"] == 16
    assert client.patch(prefix + f"/calendar/{past['RaceID']}", json={"weather": 16, "temperature": 25}).status_code == 422
    contract = client.get(prefix + "/drivers/1").json()["contract"]
    assert client.patch(prefix + f"/contracts/{contract['contract_id']}", json={"salary": 10000000, "end_season": 2028, "race_bonus": 100}).status_code == 200
    design = client.get(prefix + "/teams/3/parts").json()[0]["DesignID"]
    stats = client.get(prefix + f"/parts/{design}").json()
    stat = next(stat for stat in stats if stat["PartStat"] in (7,8,9))
    response = client.patch(prefix + f"/parts/{design}/{stat['PartStat']}", json={"value": 600})
    assert response.status_code == 200, response.text
    actual = next(row for row in response.json() if row["PartStat"] == stat["PartStat"])
    assert actual["Value"] == 600
    exported = client.post(prefix + "/export")
    assert exported.status_code == 200
    assert len(client.get(prefix).json()["changes"]) == 4
    resumed = WorkspaceStore().get(identity)
    assert resumed.db.serialize() == store.get(identity).db.serialize()
    assert len(resumed.history) == 4
