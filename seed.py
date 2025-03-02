#!/usr/bin/env python3

import sqlite3

USER_COUNT = 10000
AUTHOR_COUNT = 10**6

if __name__ == "__main__":
    db = sqlite3.connect("database.db")

    _ = db.execute("DELETE FROM users")

    params: list[str] = []

    for i in range(1, USER_COUNT + 1):
        params.append("user" + str(i))

        # NOTE: It is stupid to store the passwords in plain text, but
        # computing the hash in Python for every password while testing
        # here takes way too long. In the actual application the hashes
        # are computed.
        params.append("pwd" + str(i))

    sql = "INSERT INTO users (username, password_hash) VALUES "
    values = ["(?, ?)"] * USER_COUNT
    sql += ", ".join(values)

    _ = db.execute(sql, params)

    authors: list[tuple[str, str]] = []

    for i in range(1, AUTHOR_COUNT + 1):
        authors.append(("first_name_" + str(i), "surname_" + str(i)))

    _ = db.execute("DELETE FROM authors")

    sql = "INSERT INTO authors (first_name, surname) VALUES (?, ?)"

    for a in authors:
        _ = db.execute(sql, [a[0], a[1]])

    db.commit()
    db.close()
