from collections.abc import Sequence
from dataclasses import dataclass
from typing import TypedDict, cast

from flask import request
import db


@dataclass
class Author:
    id: int
    first_name: str | None
    surname: str


AuthorResult = TypedDict(
    "AuthorResult", {"id": int, "first_name": str | None, "surname": str}
)


def get_author_from_form():
    author_id = int(request.form["author-id"])
    author_first_name = (
        request.form["author-first-name"]
        if "author-first-name" in request.form
        else None
    )
    author_surname = request.form["author-surname"]
    form_author = Author(
        id=author_id, first_name=author_first_name, surname=author_surname
    )
    return form_author


def create_author(first_name: str | None, surname: str):
    if first_name:
        sql = "INSERT INTO authors (first_name, surname) VALUES (?, ?)"
        db.execute(sql, [first_name.strip(), surname.strip()])
    else:
        # Automatically insert NULL as the value for first name.
        sql = "INSERT INTO authors (surname) VALUES (?)"
        db.execute(sql, [surname.strip()])


def get_author(first_name: str, surname: str) -> Author | None:
    sql = "SELECT id, first_name, surname FROM authors WHERE first_name = ? AND surname = ?"
    if first_name == "":
        sql = "SELECT id, first_name, surname FROM authors WHERE first_name IS NULL AND surname = ?"
    result = db.query(
        sql, [surname] if first_name == "" else [first_name, surname]
    )

    return (
        Author(
            id=cast(int, result[0]["id"]),
            first_name=cast(str | None, result[0]["first_name"]),
            surname=cast(str, result[0]["surname"]),
        )
        if result
        else None
    )


def get_author_by_id(id: int) -> Author | None:
    sql = "SELECT id, first_name, surname FROM authors WHERE id = ?"
    result = db.query(sql, [id])

    return (
        Author(
            id=cast(int, result[0]["id"]),
            first_name=cast(str | None, result[0]["first_name"]),
            surname=cast(str, result[0]["surname"]),
        )
        if result
        else None
    )


def seach_author(first_name: str, surname: str) -> Sequence[Author]:
    sql = "SELECT id, first_name, surname FROM authors WHERE first_name LIKE ? AND surname LIKE ?"
    if first_name == "":
        sql = (
            "SELECT id, first_name, surname FROM authors WHERE surname LIKE ?"
        )
    result = db.query(
        sql,
        [f"%{surname}%"]
        if first_name == ""
        else [f"%{first_name}%", f"%{surname}%"],
    )

    authors: list[Author] = []
    for author in cast(Sequence[AuthorResult], result):
        authors.append(
            Author(
                id=author["id"],
                first_name=author["first_name"],
                surname=author["surname"],
            )
        )

    return authors
