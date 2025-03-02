#!/usr/bin/env python3

import sqlite3

if __name__ == "__main__":
    db = sqlite3.connect("database.db")

    _ = db.execute("DELETE FROM users")

    user_count = 10000

    sql = "INSERT INTO users (username, password_hash) VALUES "
    values = ["(?, ?)"] * user_count
    sql += ", ".join(values)
    params: list[str] = []

    for i in range(1, user_count + 1):
        params.append("user" + str(i))

        # NOTE: It is stupid to store the passwords in plain text, but
        # computing the hash in Python for every password while testing
        # here takes way too long. In the actual application the hashes
        # are computed.
        params.append("pwd" + str(i))

    _ = db.execute(sql, params)

    db.commit()
    db.close()
