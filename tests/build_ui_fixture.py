import json
import os
from pathlib import Path
import tempfile

from fastapi.testclient import TestClient

from backend.main import app
from backend.infrastructure import workspace


def build():
    save = Path(os.environ["F1_TEST_SAVE"]).read_bytes()
    target = Path("work/ui-fixture.json")
    target.parent.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory() as folder:
        workspace.ROOT = Path(folder)
        client = TestClient(app)
        loaded = client.post("/api/saves", files={"file": ("save5.sav", save)}).json()
        prefix = "/api/saves/" + loaded["id"]
        season = loaded['season']
        paths = ["", "/teams", "/drivers", f"/grid?year={season}", f"/grid?year={season+1}", "/compare/drivers?left=1&right=10", "/engines", "/records/seasons", f"/records?season={season}", "/performance?car=1", "/performance/history?metric=overall", "/teams/3/fitted?car=1", "/teams/3/facilities", "/teams/3/expertise-parts", f"/compare/teams?season={season}&metric=points"]
        fixture = {}
        for path in paths:
            response = client.get(prefix + path)
            if response.status_code != 200:
                raise RuntimeError(response.text)
            fixture["/api/saves/fixture" + path] = response.json()
        best = sorted((driver for driver in fixture["/api/saves/fixture/drivers"] if not driver["Retired"]), key=lambda driver: driver["average"] if driver["average"] is not None else -1, reverse=True)[:2]
        if len(best) == 2:
            path = f"/compare/drivers?left={best[0]['StaffID']}&right={best[1]['StaffID']}"
            response = client.get(prefix + path)
            if response.status_code != 200:
                raise RuntimeError(response.text)
            fixture["/api/saves/fixture" + path] = response.json()
        target.write_text(json.dumps(fixture, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    build()
