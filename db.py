from collections.abc import Sequence
import sqlite3
from typing import Any


def get_connection() -> sqlite3.Connection:
    con = sqlite3.connect("database.db")
    _ = con.execute("PRAGMA foreign_keys = ON")
    con.row_factory = sqlite3.Row
    return con


def query(sql: str, params: Sequence[Any] | None = None) -> Sequence[Any]:  # pyright: ignore[reportExplicitAny]
    if params is None:
        params = []
    con = get_connection()
    result = con.execute(sql, params).fetchall()
    con.close()
    return result
