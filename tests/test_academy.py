from backend.main import store


def candidates(client, prefix, team_id=3):
    data = client.get(prefix + "/grid").json()
    team = next(team for team in data["teams"] if team["team"]["TeamID"] == team_id)
    members = {member["driver"]["StaffID"] for member in team["academy"]}
    pool = [driver for driver in data["drivers"] if not driver["Retired"] and driver["StaffID"] not in members and driver["contract"] and driver["contract"]["Formula"] in (2, 3)]
    return team, pool


def add(client, prefix, driver_id, **options):
    return client.post(prefix + "/teams/3/academy", json={"driver_id": driver_id, "salary": 200000, "end_season": 2028, "keep_feeder_seat": True, **options})


def test_academy_has_no_small_fixed_capacity(client, loaded):
    identity, original = loaded
    prefix = f"/api/saves/{identity}"
    initial, pool = candidates(client, prefix)
    assert len(pool) >= 20
    seats = [slot["driver"]["StaffID"] if slot["driver"] else None for slot in initial["slots"]]
    for driver in pool[:20]:
        response = add(client, prefix, driver["StaffID"])
        assert response.status_code == 200, response.text
    data = client.get(prefix + "/grid").json()
    team = next(team for team in data["teams"] if team["team"]["TeamID"] == 3)
    assert len(team["academy"]) == len(initial["academy"]) + 20
    positions = [member["contract"]["PosInTeam"] for member in team["academy"]]
    assert len(positions) == len(set(positions))
    assert max(positions) > 20
    assert [slot["driver"]["StaffID"] if slot["driver"] else None for slot in team["slots"]] == seats
    assert client.post(prefix + "/export").status_code == 200


def test_academy_preserves_junior_seat_and_removal_is_scoped(client, loaded):
    identity, original = loaded
    prefix = f"/api/saves/{identity}"
    initial, pool = candidates(client, prefix)
    driver = pool[0]
    before = driver["contract"]
    assert add(client, prefix, driver["StaffID"]).status_code == 200
    current = store.get(identity)
    assert current.rows("SELECT c.rowid AS contract_id,c.*,t.Formula,t.TeamName FROM Staff_Contracts c JOIN Teams t USING(TeamID) WHERE c.rowid=?", (before["contract_id"],))[0] == before
    assert current.scalar("SELECT AffiliateDualRoleClause FROM Staff_Contracts WHERE StaffID=? AND TeamID=3 AND PosInTeam>2 AND ContractType=0", (driver["StaffID"],)) == 1
    assert add(client, prefix, driver["StaffID"]).status_code == 422
    snapshot = current.db.serialize()
    assert client.delete(prefix + f"/teams/3/academy/{driver['StaffID']}").status_code == 200
    assert current.scalar("SELECT COUNT(*) FROM Staff_Contracts WHERE rowid=?", (before["contract_id"],)) == 1
    assert client.post(prefix + "/undo").status_code == 200
    assert current.db.serialize() == snapshot


def test_academy_member_can_be_promoted_to_car_one(client, loaded):
    identity, original = loaded
    prefix = f"/api/saves/{identity}"
    initial, pool = candidates(client, prefix)
    driver_id = pool[0]["StaffID"]
    assert add(client, prefix, driver_id).status_code == 200
    edit = {"driver_id": driver_id, "team_id": 3, "seat": 1, "timing": "now", "displaced": "reserve", "salary": 3000000, "end_season": 2028}
    preview = client.post(prefix + "/transfers/preview", json=edit).json()
    edit["expected_outgoing"] = preview["outgoing"]["StaffID"]
    response = client.post(prefix + "/transfers", json=edit)
    assert response.status_code == 200, response.text
    team = next(team for team in client.get(prefix + "/grid").json()["teams"] if team["team"]["TeamID"] == 3)
    assert team["slots"][0]["driver"]["StaffID"] == driver_id
    assert driver_id not in {member["driver"]["StaffID"] for member in team["academy"]}
    assert edit["expected_outgoing"] in {member["driver"]["StaffID"] for member in team["academy"]}


def test_future_academy_projects_without_changing_current_grid(client, loaded):
    identity, original = loaded
    prefix = f"/api/saves/{identity}"
    initial, pool = candidates(client, prefix)
    driver_id = pool[0]["StaffID"]
    assert add(client, prefix, driver_id, timing="next").status_code == 200
    data = client.get(prefix + "/grid").json()
    team = next(team for team in data["teams"] if team["team"]["TeamID"] == 3)
    assert driver_id not in {member["driver"]["StaffID"] for member in team["academy"]}
    year = store.get(identity).season + 1
    future = client.get(prefix + f"/grid?year={year}").json()
    team = next(team for team in future["teams"] if team["team"]["TeamID"] == 3)
    member = next(member for member in team["academy"] if member["driver"]["StaffID"] == driver_id)
    assert member["contract"]["ContractType"] == 3
