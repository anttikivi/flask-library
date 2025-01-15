from werkzeug.security import generate_password_hash

import db


def get_users_by_name(username: str):
    sql = "SELECT id, username FROM users WHERE username = ?"
    result = db.query(sql, [username])
    return result[0] if result else None


def create_user(username: str, password: str):
    password_hash = generate_password_hash(password)
    sql = "INSERT INTO users (username, password_hash) VALUES (?, ?)"
    db.execute(sql, [username, password_hash])


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
