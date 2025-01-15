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
