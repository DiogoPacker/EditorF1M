"""Synthetic saves exercise capabilities without distributing a game save."""
import sqlite3

import pytest

from backend.main import store
from backend.infrastructure.codec import SaveContainer


@pytest.fixture
def plain(client):
    db = sqlite3.connect(":memory:")
    db.executescript("""
        CREATE TABLE Player_State(CurrentSeason INTEGER, Day INTEGER);
        INSERT INTO Player_State VALUES(1888,1);
        CREATE TABLE Staff_BasicData(StaffID INTEGER);
        CREATE TABLE Teams(TeamID INTEGER PRIMARY KEY,Formula INTEGER,TeamName TEXT,TeamNameLocKey TEXT,IsCustomTeam INTEGER);
        INSERT INTO Teams VALUES(45,1,'Fiction Racing','[TeamName_Original]',0),(98,1,'Other Team','[STRING_LITERAL:Value=|Equipe Inventada|]',1);
        CREATE TABLE Finance_TeamBalance(TeamID INTEGER,Balance INTEGER);
        INSERT INTO Finance_TeamBalance VALUES(45,1000),(98,2000);
        CREATE TABLE Races_TeamStandings(TeamID INTEGER,SeasonID INTEGER,Points INTEGER,Position INTEGER);
        INSERT INTO Races_TeamStandings VALUES(45,1888,30,1),(98,1888,20,2);
        CREATE TABLE Teams_Colours(ColourID INTEGER PRIMARY KEY,TeamID INTEGER,Colour INTEGER);
        INSERT INTO Teams_Colours VALUES(1,45,4281558681),(2,98,4291559424);
        CREATE TABLE Parts_Designs(DesignID INTEGER PRIMARY KEY,TeamID INTEGER,PartType INTEGER);
        INSERT INTO Parts_Designs VALUES(1,45,0),(2,45,1),(3,45,2),(4,98,0),(5,98,1),(6,98,2);
        CREATE TABLE Parts_Designs_StatValues(DesignID INTEGER,PartStat INTEGER,Value REAL,UnitValue REAL);
        INSERT INTO Parts_Designs_StatValues VALUES(1,10,600,92),(1,6,580,79),(1,14,700,74),(2,15,500,60),(3,15,600,62);
        INSERT INTO Parts_Designs_StatValues SELECT DesignID+3,PartStat,Value,UnitValue FROM Parts_Designs_StatValues WHERE DesignID<4;
        CREATE TABLE Parts_Enum_EngineManufacturers(Value INTEGER,Name TEXT,EngineDesignID INTEGER,ErsDesignID INTEGER,GearboxDesignID INTEGER);
        INSERT INTO Parts_Enum_EngineManufacturers VALUES(1,'Fiction Power',1,2,3),(2,'Other Power',4,5,6);
        CREATE TABLE Parts_TeamHistory(TeamID INTEGER,SeasonID INTEGER,EngineManufacturer INTEGER);
        INSERT INTO Parts_TeamHistory VALUES(45,1888,1),(98,1888,2);
        CREATE TABLE Buildings(BuildingID INTEGER PRIMARY KEY,Type INTEGER,Name TEXT,UpgradeLevel INTEGER,RequiredType INTEGER,RequiredLevel INTEGER);
        INSERT INTO Buildings VALUES(501,7,'Fiction Facility',1,NULL,NULL),(502,7,'Fiction Facility',2,NULL,NULL),(601,8,'Requires level 3',1,7,3);
        CREATE TABLE Buildings_HQ(TeamID INTEGER,BuildingID INTEGER,BuildingType INTEGER,DegradationValue REAL,BuildingState INTEGER);
        INSERT INTO Buildings_HQ VALUES(45,501,7,0.78,2),(98,501,7,0.91,2),(45,601,8,1,2);
        CREATE TABLE Buildings_HQ_History(BuildingID INTEGER,Type INTEGER,TeamID INTEGER,DayConstructed INTEGER,PRIMARY KEY(BuildingID,Type,TeamID));
        CREATE TABLE Parts_TeamExpertise(TeamID INTEGER,PartType INTEGER,PartStat INTEGER,Expertise REAL,NextSeasonExpertise REAL);
        INSERT INTO Parts_TeamExpertise VALUES(45,3,4,500.25,450.25),(45,3,15,300.75,290.75);
        CREATE TABLE Races(RaceID INTEGER,SeasonID INTEGER,TrackID INTEGER,Day INTEGER);
        INSERT INTO Races VALUES(1,1888,1,1),(2,1888,2,2),(3,1888,3,3);
        CREATE TABLE Races_Tracks(TrackID INTEGER,Name TEXT);
        INSERT INTO Races_Tracks VALUES(1,'Fiction One'),(2,'Fiction Two'),(3,'Future');
        CREATE TABLE Races_Results(Season INTEGER,RaceID INTEGER,TeamID INTEGER,FinishingPos INTEGER,Points INTEGER,DNF INTEGER);
        INSERT INTO Races_Results VALUES(1888,1,45,1,25,0),(1888,1,98,2,18,0),(1888,2,45,0,0,1),(1888,2,98,1,25,0);
        CREATE TABLE Races_SprintResults(SeasonID INTEGER,RaceID INTEGER,TeamID INTEGER,ChampionshipPoints INTEGER,RaceFormula INTEGER);
        INSERT INTO Races_SprintResults VALUES(1888,1,45,8,1),(1888,1,98,7,1);
        CREATE TABLE Races_QualifyingResults(SeasonID INTEGER,RaceID INTEGER,TeamID INTEGER,FinishingPos INTEGER,QualifyingStage INTEGER,SprintShootout INTEGER,RaceFormula INTEGER);
        INSERT INTO Races_QualifyingResults VALUES(1888,1,45,1,2,0,1),(1888,1,98,2,2,0,1),(1888,2,45,1,1,0,1),(1888,2,98,1,2,0,1);
    """)
    response = client.post('/api/saves', files={'file': ('fiction.sqlite', db.serialize())})
    db.close()
    assert response.status_code == 201, response.text
    identity = response.json()['id']
    return '/api/saves/' + identity, store.get(identity)


def test_identity_is_read_from_save_and_survives_export_undo(client, plain):
    prefix, current = plain
    original = current.db.serialize()
    teams = client.get(prefix + '/teams').json()
    assert teams[0]['name'] == 'Fiction Racing'
    assert teams[1]['name'] == 'Equipe Inventada'
    response = client.patch(prefix + '/teams/45/identity', json={'name': 'Aurora GP', 'color': '#123abc'})
    assert response.status_code == 200, response.text
    assert response.json()['color'] == '#123abc'
    exported = client.post(prefix + '/export?format=sqlite')
    parsed = SaveContainer.parse(exported.content)
    assert parsed.database == current.db.serialize()
    assert current.scalar('SELECT TeamNameLocKey FROM Teams WHERE TeamID=45') == '[STRING_LITERAL:Value=|Aurora GP|]'
    assert client.patch(prefix + '/teams/45/identity', json={'name': '[bad]', 'color': '#123abc'}).status_code == 422
    assert client.post(prefix + '/undo').status_code == 200
    assert current.db.serialize() == original


def test_facility_levels_condition_prerequisites_and_undo(client, plain):
    prefix, current = plain
    before = current.db.serialize()
    data = client.get(prefix + '/teams/45/facilities').json()
    assert data['supported'] and data['facilities'][0]['condition'] == 78
    response = client.patch(prefix + '/teams/45/facilities/7', json={'building_id': 502, 'condition': 95.5})
    assert response.status_code == 200, response.text
    assert current.scalar('SELECT BuildingID FROM Buildings_HQ WHERE TeamID=45 AND BuildingType=7') == 502
    assert current.scalar('SELECT DegradationValue FROM Buildings_HQ WHERE TeamID=45 AND BuildingType=7') == .955
    assert current.scalar('SELECT DegradationValue FROM Buildings_HQ WHERE TeamID=98') == .91
    assert client.patch(prefix + '/teams/45/facilities/7', json={'building_id': 601, 'condition': 99}).status_code == 422
    assert client.patch(prefix + '/teams/45/facilities/8', json={'building_id': 601, 'condition': 99}).status_code == 422
    client.post(prefix + '/undo')
    assert current.db.serialize() == before


def test_expertise_batch_float_target_and_atomicity(client, plain):
    prefix, current = plain
    data = client.get(prefix + '/teams/45/expertise-parts').json()
    assert data['parts'][0]['stats'][1]['direction'] == -1
    response = client.patch(prefix + '/teams/45/expertise-parts/3', json={'target': 'next', 'stats': {'4': 460.25, '15': 280.75}})
    assert response.status_code == 200, response.text
    assert current.scalar('SELECT Expertise FROM Parts_TeamExpertise WHERE PartStat=4') == 500.25
    assert current.scalar('SELECT NextSeasonExpertise FROM Parts_TeamExpertise WHERE PartStat=4') == 460.25
    before = current.db.serialize()
    assert client.patch(prefix + '/teams/45/expertise-parts/3', json={'stats': {'4': 999, '15': 1001}}).status_code == 422
    assert current.db.serialize() == before


def test_team_comparison_uses_fictional_season_sprints_and_final_qualifying(client, plain):
    prefix, current = plain
    response = client.get(prefix + '/compare/teams')
    assert response.status_code == 200, response.text
    data = response.json()
    assert data['season'] == 1888
    assert data['series'][0]['values'] == [33,33,None]
    assert data['series'][1]['values'] == [25,50,None]
    assert data['summary'][0]['dnfs'] == 1
    assert data['summary'][0]['race_positions']['2'] > data['summary'][1]['race_positions']['2']
    assert data['summary'][0]['poles'] == data['summary'][1]['poles'] == 1
    assert data['summary'][0]['qualifying_positions']['2'] > data['summary'][1]['qualifying_positions']['2']
    assert client.get(prefix + '/compare/teams?season=1889').json()['labels'] == []
    assert client.get(prefix + '/compare/teams?metric=invalid').status_code == 422


def test_native_engines_work_without_custom_mod_tables(client, plain):
    prefix, current = plain
    data = client.get(prefix + '/engines').json()
    assert data['supported'] and data['mode'] == 'native'
    assert not data['create_supported'] and not data['allocation_supported']
    response = client.patch(prefix + '/engines/1', json={'name': 'Fiction Power 2', 'power': 94.5, 'durability': 56.5})
    assert response.status_code == 200, response.text
    assert current.scalar('SELECT UnitValue FROM Parts_Designs_StatValues WHERE DesignID=1 AND PartStat=10') == 94.5
    assert current.scalar('SELECT UnitValue FROM Parts_Designs_StatValues WHERE DesignID=4 AND PartStat=10') == 92
    assert client.post(prefix + '/engines', json={'name':'Unsupported','base_engine':1}).status_code == 422


def test_missing_optional_tables_report_unsupported_instead_of_faking_data(client, plain):
    prefix, current = plain
    current.db.executescript('DROP TABLE Buildings_HQ; DROP TABLE Parts_TeamExpertise; DROP TABLE Teams_Colours; DROP TABLE Parts_Enum_EngineManufacturers;')
    assert not client.get(prefix + '/teams/45/facilities').json()['supported']
    assert not client.get(prefix + '/teams/45/expertise-parts').json()['supported']
    assert not client.get(prefix + '/engines').json()['supported']
    assert not client.get(prefix + '/teams').json()[0]['color_editable']
    assert client.patch(prefix + '/teams/45/identity', json={'name':'Valid','color':'#123abc'}).status_code == 422


def test_real_save_management_export_roundtrip_and_undo(client, loaded):
    identity, original = loaded
    prefix = '/api/saves/' + identity
    current = store.get(identity)
    before = current.db.serialize()
    assert client.patch(prefix + '/teams/3/identity', json={'name':'Equipe Fictícia GP','color':'#2468ac'}).status_code == 200
    facility = next(item for item in client.get(prefix + '/teams/3/facilities').json()['facilities'] if item['editable'])
    response = client.patch(prefix + '/teams/3/facilities/' + str(facility['BuildingType']), json={'building_id':facility['BuildingID'],'condition':87.25})
    assert response.status_code == 200, response.text
    part = client.get(prefix + '/teams/3/expertise-parts').json()['parts'][0]
    stat = part['stats'][0]
    response = client.patch(prefix + '/teams/3/expertise-parts/' + str(part['part_type']), json={'target':'current','stats':{str(stat['PartStat']):min(1000,stat['Expertise']+10)}})
    assert response.status_code == 200, response.text
    data = client.get(prefix + '/compare/teams').json()
    assert data['season'] == current.season
    assert any(row['name'] == 'Equipe Fictícia GP' for row in data['series'])
    exported = client.post(prefix + '/export')
    assert exported.status_code == 200
    assert SaveContainer.parse(exported.content).database == current.db.serialize()
    for _ in range(3):
        assert client.post(prefix + '/undo').status_code == 200
    assert current.db.serialize() == before
    assert current.container.original == original
