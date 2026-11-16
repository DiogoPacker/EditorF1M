from . import services


def fitted(workspace, team_id, car):
    rows = workspace.rows("SELECT l.*,d.DesignNumber FROM Parts_CarLoadout l JOIN Parts_Designs d USING(DesignID) WHERE l.TeamID=? AND l.LoadoutID=? AND l.PartType BETWEEN 3 AND 8 ORDER BY l.PartType", (team_id, car))
    for row in rows:
        row["part"] = services.PART_LABELS[row["PartType"]]
        row["stats"] = services.part_stats(workspace, row["DesignID"])
        for stat in row["stats"]:
            stat["minimum_unit"] = services.unit_value(stat["PartStat"], 0, row["PartType"])
            stat["maximum_unit"] = services.unit_value(stat["PartStat"], 1000, row["PartType"])
        row["shared_cars"] = [value["LoadoutID"] for value in workspace.rows("SELECT LoadoutID FROM Parts_CarLoadout WHERE TeamID=? AND DesignID=?", (team_id, row["DesignID"]))]
    return {"team_id": team_id, "car": car, "parts": rows}


def raw_from_unit(stat_id, value, part_type):
    low = services.unit_value(stat_id, 0, part_type)
    high = services.unit_value(stat_id, 1000, part_type)
    raw = (value - low) / (high - low) * 1000
    if not 0 <= raw <= 1000:
        raise ValueError(f"Atributo {stat_id}: valor convertido deve ficar entre {low:.3f} e {high:.3f}.")
    return raw


def edit_fitted(workspace, team_id, car, edit):
    loadout = fitted(workspace, team_id, car)
    designs = {part["DesignID"]: part for part in loadout["parts"]}
    changes = []
    seen = set()
    for item in edit.stats:
        if (item.design_id, item.stat_id) in seen:
            raise ValueError("O lote contém um atributo repetido.")
        seen.add((item.design_id, item.stat_id))
        part = designs.get(item.design_id)
        if not part:
            raise ValueError("O design não está instalado neste carro. Atualize a tela.")
        stat = next((stat for stat in part["stats"] if stat["PartStat"] == item.stat_id), None)
        if not stat:
            raise ValueError("Atributo não encontrado nesta peça.")
        raw = raw_from_unit(item.stat_id, item.value, part["PartType"]) if edit.units == "converted" else item.value
        if not 0 <= raw <= 1000:
            raise ValueError("Valor bruto deve ficar entre 0 e 1000.")
        converted = services.unit_value(item.stat_id, raw, part["PartType"])
        changes.append((raw, converted, item.design_id, item.stat_id))
    def operation():
        for row in changes:
            workspace.db.execute("UPDATE Parts_Designs_StatValues SET Value=?,UnitValue=? WHERE DesignID=? AND PartStat=?", row)
    workspace.change(f"Peças instaladas · equipe #{team_id} / carro {car} · {len(changes)} atributos", operation)
    return fitted(workspace, team_id, car)
