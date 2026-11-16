TEAMS = {
    1: ("Ferrari", "#ed3947", "FER"),
    2: ("McLaren", "#ff9800", "MCL"),
    3: ("Red Bull Racing", "#5285ff", "RBR"),
    4: ("Mercedes", "#28dfbd", "MER"),
    5: ("Alpine", "#ef85bc", "ALP"),
    6: ("Williams", "#47b9ed", "WIL"),
    7: ("Haas", "#d5d7dc", "HAS"),
    8: ("Racing Bulls", "#8a9bff", "RB"),
    9: ("Audi", "#f44753", "AUD"),
    10: ("Aston Martin", "#48b698", "AST"),
}


def identity(team_id, fallback="Equipe", custom=False):
    if custom:
        return "Cadillac", "#d4b88c", "CAD"
    return TEAMS.get(team_id, (fallback, "#d4b88c", fallback[:3].upper()))


def team_color(name):
    if name == "Cadillac":
        return "#d4b88c"
    return next((color for label, color, code in TEAMS.values() if label == name), "#aab7d0")
