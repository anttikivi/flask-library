import db


def get_users_by_name(username: str):
    sql = "SELECT id, username FROM users WHERE username = ?"
    result = db.query(sql, [username])
    return result[0] if result else None
