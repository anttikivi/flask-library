#!/usr/bin/env python3

import random
import sqlite3

USER_COUNT = 10000
AUTHOR_COUNT = 10**6
BOOK_PER_AUTHOR_COUNT = 10
REVIEW_COUNT = 10**5

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

    _ = db.execute("DELETE FROM books")

    sql = "INSERT INTO books (isbn, name, author_id, class_id) VALUES "
    values = ["(?, ?, ?, ?)"] * BOOK_PER_AUTHOR_COUNT
    sql += ", ".join(values)

    for i in range(1, AUTHOR_COUNT + 1):
        params: list[str | int] = []
        for j in range(1, BOOK_PER_AUTHOR_COUNT + 1):
            id = str((i + j) * i * j)
            params.append(id)
            params.append("book" + id)
            params.append(i)
            params.append(random.randint(1, 2000))
        _ = db.execute(sql, params)

    _ = db.execute("DELETE FROM reviews")

    sql = """
        INSERT INTO reviews (
            user_id,
            book_id,
            stars,
            message,
            time,
            last_edited
        )
        VALUES (?, ?, ?, ?, datetime('now'), datetime('now'))
    """

    for i in range(1, REVIEW_COUNT + 1):
        _ = db.execute(sql, [1, 1, random.randint(1, 5), "message " + str(i)])

    db.commit()
    db.close()
