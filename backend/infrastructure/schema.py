"""Inspect capabilities instead of inferring compatibility from a mod name."""


def columns(workspace, table):
    quoted = '"' + table.replace('"', '""') + '"'
    return {row["name"] for row in workspace.rows(f"PRAGMA table_info({quoted})")}


def has_columns(workspace, table, required):
    return set(required) <= columns(workspace, table)
