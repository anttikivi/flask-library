import sqlite3
from collections.abc import Sequence
from typing import Any

from flask import g


def get_connection() -> sqlite3.Connection:
    con = sqlite3.connect("database.db")
    _ = con.execute("PRAGMA foreign_keys = ON")
    # Old factory: con.row_factory = sqlite3.Row
    con.row_factory = dict_factory
    return con


def dict_factory(
    cursor: sqlite3.Cursor,
    row: tuple[Any, ...],  # pyright: ignore[reportExplicitAny]
) -> dict[str, Any]:  # pyright: ignore[reportExplicitAny]
    fields = [column[0] for column in cursor.description]
    return {key: value for key, value in zip(fields, row)}  # pyright: ignore[reportAny]


def execute(sql: str, params: Sequence[Any] | None = None) -> None:  # pyright: ignore[reportExplicitAny]
    if params is None:
        params = []
    con = get_connection()
    result = con.execute(sql, params)
    con.commit()
    g.last_insert_id = result.lastrowid
    con.close()


def last_insert_id() -> Any:  # pyright: ignore[reportAny,reportExplicitAny]
    return g.last_insert_id  # pyright: ignore[reportAny]


def query(sql: str, params: Sequence[Any] | None = None) -> Sequence[Any]:  # pyright: ignore[reportExplicitAny]
    if params is None:
        params = []
    con = get_connection()
    result = con.execute(sql, params).fetchall()
    con.close()
    return result
