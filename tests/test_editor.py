import sqlite3

import pytest

from backend.infrastructure.codec import SaveContainer
from backend.main import store


def driver_transfer(client, identity, **options):
    prefix = f"/api/saves/{identity}"
    grid = client.get(prefix + "/grid").json()
    candidate = next(driver for driver in grid["drivers"] if not driver["Retired"] and driver["contract"] and driver["contract"]["Formula"] == 2 and driver["contract"]["PosInTeam"] in (1, 2))
    edit = {"driver_id": candidate["StaffID"], "team_id": 3, "seat": 2, "timing": "now", "displaced": "release", "salary": 3000000, "end_season": 2028, **options}
    preview = client.post(prefix + "/transfers/preview", json=edit)
    assert preview.status_code == 200, preview.text
    edit["expected_outgoing"] = preview.json()["outgoing"]["StaffID"] if preview.json()["outgoing"] else None
    return edit, preview.json()


@pytest.mark.parametrize("displaced", ["release", "swap", "reserve"])
def test_promote_f2_and_resolve_occupied_seat(client, loaded, displaced):
    identity, original = loaded
    prefix = f"/api/saves/{identity}"
    current = store.get(identity)
    original_results = current.rows("SELECT * FROM Races_Results ORDER BY Season,RaceID,FinishingPos")
    before = current.db.serialize()
    edit, preview = driver_transfer(client, identity, displaced=displaced)
    response = client.post(prefix + "/transfers", json=edit)
    assert response.status_code == 200, response.text
    current_driver = client.get(prefix + f"/drivers/{edit['driver_id']}").json()
    assert current_driver["contract"]["TeamID"] == 3
    assert current_driver["contract"]["PosInTeam"] == 2
    assert current.scalar("SELECT HasSuperLicense FROM Staff_DriverData WHERE StaffID=?", (edit["driver_id"],)) == 1
    outgoing = client.get(prefix + f"/drivers/{edit['expected_outgoing']}").json()
    if displaced == "release":
        assert outgoing["contract"] is None
    elif displaced == "reserve":
        assert outgoing["contract"]["TeamID"] == 3 and outgoing["contract"]["PosInTeam"] > 2
    else:
        assert outgoing["contract"]["TeamID"] == preview["origin"]["TeamID"]
        assert outgoing["contract"]["PosInTeam"] == preview["origin"]["PosInTeam"]
    assert current.rows("SELECT * FROM Races_Results ORDER BY Season,RaceID,FinishingPos") == original_results
    exported = client.post(prefix + "/export")
    assert exported.status_code == 200
    assert SaveContainer.parse(exported.content).auxiliary == SaveContainer.parse(original).auxiliary
    assert client.post(prefix + "/undo").status_code == 200
    assert current.db.serialize() == before


def test_future_grid_and_contract_badge(client, loaded):
    identity, original = loaded
    prefix = f"/api/saves/{identity}"
    current = store.get(identity)
    grid_before = client.get(prefix + "/grid").json()
    edit, preview = driver_transfer(client, identity, timing="next", seat=1)
    response = client.post(prefix + "/transfers", json=edit)
    assert response.status_code == 200, response.text
    grid_after = client.get(prefix + "/grid").json()
    ids_before = [[slot["driver"]["StaffID"] if slot["driver"] else None for slot in team["slots"]] for team in grid_before["teams"]]
    ids_after = [[slot["driver"]["StaffID"] if slot["driver"] else None for slot in team["slots"]] for team in grid_after["teams"]]
    assert ids_before == ids_after
    future = client.get(prefix + f"/grid?year={current.season + 1}").json()
    target = next(team for team in future["teams"] if team["team"]["TeamID"] == 3)
    assert target["slots"][0]["driver"]["StaffID"] == edit["driver_id"]
    contract = client.get(prefix + f"/drivers/{edit['driver_id']}").json()["future_contracts"][0]
    assert client.patch(prefix + f"/contracts/{contract['contract_id']}", json={"salary": 4000000, "end_season": 2029, "race_bonus": 500}).status_code == 200
    assert client.delete(prefix + f"/drivers/{edit['driver_id']}/future-contract").status_code == 200


def test_transfer_stale_preview_rejected_without_changes(client, loaded):
    identity, original = loaded
    prefix = f"/api/saves/{identity}"
    edit, preview = driver_transfer(client, identity)
    edit["expected_outgoing"] = 999999
    before = store.get(identity).db.serialize()
    assert client.post(prefix + "/transfers", json=edit).status_code == 422
    assert store.get(identity).db.serialize() == before


def test_engine_profile_creation_assignment_and_client_sync(client, loaded):
    identity, original = loaded
    prefix = f"/api/saves/{identity}"
    response = client.post(prefix + "/engines", json={"name": "Studio Power", "base_engine": 4})
    assert response.status_code == 201, response.text
    engine = response.json()
    assert client.patch(prefix + "/teams/3/engine", json={"engine_id": engine["engineId"]}).status_code == 200
    edit = {"name": "Studio Power V2", "power": 98, "fuel": 82, "durability": 70, "ers": 65, "gearbox": 63}
    assert client.patch(prefix + f"/engines/{engine['engineId']}", json=edit).status_code == 200
    current = store.get(identity)
    row = current.rows("SELECT s.UnitValue FROM Parts_CarLoadout l JOIN Parts_Designs_StatValues s USING(DesignID) WHERE l.TeamID=3 AND l.LoadoutID=1 AND l.PartType=0 AND s.PartStat=10")[0]
    assert row["UnitValue"] == 98
    other = current.rows("SELECT s.UnitValue FROM Parts_CarLoadout l JOIN Parts_Designs_StatValues s USING(DesignID) WHERE l.TeamID=8 AND l.LoadoutID=1 AND l.PartType=0 AND s.PartStat=10")[0]
    assert other["UnitValue"] == 96
    assert client.post(prefix + "/export").status_code == 200


def test_fitted_batch_converts_values_and_is_atomic(client, loaded):
    identity, original = loaded
    prefix = f"/api/saves/{identity}"
    current = store.get(identity)
    response = client.get(prefix + "/teams/3/fitted")
    assert response.status_code == 200, response.text
    part = next(part for part in response.json()["parts"] if part["PartType"] == 7)
    stat = next(stat for stat in part["stats"] if stat["PartStat"] == 9)
    edit = {"units": "converted", "stats": [{"design_id": part["DesignID"], "stat_id": 9, "value": stat["UnitValue"] + .01}]}
    assert client.patch(prefix + "/teams/3/fitted", json=edit).status_code == 200
    actual = current.scalar("SELECT UnitValue FROM Parts_Designs_StatValues WHERE DesignID=? AND PartStat=9", (part["DesignID"],))
    assert actual == pytest.approx(stat["UnitValue"] + .01)
    before = current.db.serialize()
    edit["stats"].append({"design_id": 999999, "stat_id": 9, "value": 8})
    assert client.patch(prefix + "/teams/3/fitted", json=edit).status_code == 422
    assert current.db.serialize() == before


def test_records_include_main_sprint_and_correct_points(client, loaded):
    identity, original = loaded
    prefix = f"/api/saves/{identity}"
    years = client.get(prefix + "/records/seasons").json()
    assert 2026 in years
    records = client.get(prefix + "/records?season=2026").json()
    assert records["races"] and records["drivers"]
    for driver in records["drivers"]:
        points = sum((cell["race"]["Points"] if cell["race"] else 0) + (cell["sprint"]["Points"] if cell["sprint"] else 0) for cell in driver["cells"])
        assert points == driver["result_points"]
    history = client.get(prefix + "/performance/history?metric=overall").json()
    assert len(history["labels"]) == len(records["races"])
    assert any(value is None for value in history["series"][0]["values"])
