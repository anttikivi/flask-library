import db


def create_library(user_id: int):
    sql = "INSERT INTO libraries (user_id) VALUES (?)"
    db.execute(sql, [user_id])
