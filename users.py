from dataclasses import dataclass
from typing import cast
from werkzeug.security import check_password_hash, generate_password_hash

import db


@dataclass
class User:
    id: int
    username: str


def get_users_by_name(username: str):
    sql = "SELECT id, username FROM users WHERE username = ?"
    result = db.query(sql, [username])
    return (
        User(
            id=cast(int, result[0]["id"]),
            username=cast(str, result[0]["username"]),
        )
        if result
        else None
    )


def create_user(username: str, password: str):
    password_hash = generate_password_hash(password)
    sql = "INSERT INTO users (username, password_hash) VALUES (?, ?)"
    db.execute(sql, [username, password_hash])


def change_username(user_id: int, new_username: str):
    sql = "UPDATE users SET username = ? WHERE id = ?"
    db.execute(sql, [new_username, user_id])


def check_login(username: str, password: str) -> int | None:
    sql = "SELECT id, password_hash FROM users WHERE username = ?"
    result = db.query(sql, [username])
    if not result:
        return None

    user_id = cast(int, result[0]["id"])
    password_hash = cast(str, result[0]["password_hash"])
    if check_password_hash(password_hash, password):
        return user_id
    else:
        return None


def is_valid_username(username: str) -> bool:
    if len(username) > 16:
        return False

    for c in username:
        # The program requires the username to consist of alphanumeric
        # ASCII characters and hyphens and underscores.
        if not (
            (c.isalpha() and c.isascii())
            or c.isdigit()
            or c == "-"
            or c == "_"
        ):
            return False

    return True
