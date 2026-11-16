from backend.main import store


def test_release_current_seat_keeps_results_and_is_undoable(client,loaded):
    identity,original=loaded
    prefix=f"/api/saves/{identity}"
    current=store.get(identity)
    team=next(team for team in client.get(prefix+'/grid').json()['teams'] if team['team']['TeamID']==3)
    driver=team['slots'][0]['driver']['StaffID']
    before=current.db.serialize()
    results=current.rows('SELECT * FROM Races_Results')
    response=client.delete(prefix+f'/teams/3/seats/1?expected_driver={driver}')
    assert response.status_code==200,response.text
    team=next(team for team in client.get(prefix+'/grid').json()['teams'] if team['team']['TeamID']==3)
    assert team['slots'][0]['driver'] is None
    assert current.rows('SELECT * FROM Races_Results')==results
    assert client.post(prefix+'/undo').status_code==200
    assert current.db.serialize()==before


def test_release_future_continuing_seat_does_not_remove_current_driver(client,loaded):
    identity,original=loaded
    prefix=f"/api/saves/{identity}"
    year=store.get(identity).season+1
    target=next(team for team in client.get(prefix+f'/grid?year={year}').json()['teams'] if team['team']['TeamID']==3)
    driver=target['slots'][0]['driver']['StaffID']
    assert client.delete(prefix+f'/teams/3/seats/1?expected_driver={driver}&timing=next').status_code==200
    current=next(team for team in client.get(prefix+'/grid').json()['teams'] if team['team']['TeamID']==3)
    future=next(team for team in client.get(prefix+f'/grid?year={year}').json()['teams'] if team['team']['TeamID']==3)
    assert current['slots'][0]['driver']['StaffID']==driver
    assert future['slots'][0]['driver'] is None


def test_stale_drop_cannot_release_a_different_driver(client,loaded):
    identity,original=loaded
    prefix=f"/api/saves/{identity}"
    before=store.get(identity).db.serialize()
    assert client.delete(prefix+'/teams/3/seats/1?expected_driver=999999').status_code==422
    assert store.get(identity).db.serialize()==before


def test_removing_projected_academy_preserves_current_membership(client,loaded):
    identity,original=loaded
    prefix=f"/api/saves/{identity}"
    current=store.get(identity)
    year=current.season+1
    future=next(team for team in client.get(prefix+f'/grid?year={year}').json()['teams'] if team['team']['TeamID']==3)
    member=next(member for member in future['academy'] if member['contract']['ContractType']==0)
    driver=member['driver']['StaffID']
    response=client.delete(prefix+f'/teams/3/academy/{driver}?timing=next')
    assert response.status_code==200,response.text
    current_grid=next(team for team in client.get(prefix+'/grid').json()['teams'] if team['team']['TeamID']==3)
    future_grid=next(team for team in client.get(prefix+f'/grid?year={year}').json()['teams'] if team['team']['TeamID']==3)
    assert driver in [member['driver']['StaffID'] for member in current_grid['academy']]
    assert driver not in [member['driver']['StaffID'] for member in future_grid['academy']]
