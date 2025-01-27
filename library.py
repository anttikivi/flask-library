from collections.abc import Sequence
from dataclasses import dataclass
from typing import TypedDict, cast

import db


@dataclass
class Book:
    id: int
    isbn: str | None
    name: str
    author: int
    classification: int


@dataclass
class LibraryClass:
    id: int
    key: str
    label: str


BooksResult = TypedDict(
    "BooksResult",
    {
        "id": int,
        "isbn": str | None,
        "name": str,
        "author_id": int,
        "class_id": int,
    },
)


LibraryClassResult = TypedDict(
    "LibraryClassResult", {"id": int, "key": str, "label": str}
)


def create_library(user_id: int):
    sql = "INSERT INTO libraries (user_id) VALUES (?)"
    db.execute(sql, [user_id])


def create_book(isbn: str | None, name: str, author_id: int, class_id: int):
    sql = "INSERT INTO books (isbn, name, author_id, class_id) VALUES (?, ?, ?, ?)"
    db.execute(sql, [isbn, name, author_id, class_id])


def get_user_library(user_id: int) -> int | None:
    sql = "SELECT id FROM libraries WHERE user_id = ?"
    result = db.query(sql, [user_id])
    return result[0]["id"] if result else None


def add_book_to_user(book_id: int, user_id: int):
    sql = "INSERT INTO book_ownerships (book_id, library_id) VALUES (?, (SELECT id FROM libraries WHERE user_id = ?))"
    db.execute(sql, [book_id, user_id])


def get_book_by_id(id: int) -> Book | None:
    sql = "SELECT id, isbn, name, author_id, class_id FROM books WHERE id = ?"
    result = db.query(sql, [id])

    return (
        Book(
            id=cast(int, result[0]["id"]),
            isbn=cast(str | None, result[0]["isbn"]),
            name=cast(str, result[0]["name"]),
            author=cast(int, result[0]["author_id"]),
            classification=cast(int, result[0]["class_id"]),
        )
        if result
        else None
    )


def is_owner(user_id: int, book_id: int) -> bool:
    """
    Checks whether the given user owns a copy of the given book.
    """
    sql = "SELECT COUNT(o.id) AS count FROM book_ownerships AS o, libraries AS l WHERE o.library_id = l.id AND l.user_id = ? AND o.book_id = ?;"
    result = db.query(sql, [user_id, book_id])

    return result[0]["count"] > 0 if result else False


def search_books_from_author(author_id: int, book_name: str):
    sql = "SELECT id, isbn, name, author_id, class_id FROM books WHERE author_id = ? AND name LIKE ?"
    result = db.query(sql, [author_id, f"%{book_name}%"])

    books: list[Book] = []
    for book in cast(Sequence[BooksResult], result):
        books.append(
            Book(
                id=book["id"],
                isbn=book["isbn"],
                name=book["name"],
                author=book["author_id"],
                classification=book["class_id"],
            )
        )

    return books


def get_classification_by_id(id: int) -> LibraryClass | None:
    sql = "SELECT id, key, label FROM classification WHERE id = ?"
    result = db.query(sql, [id])

    return (
        LibraryClass(
            id=cast(int, result[0]["id"]),
            key=cast(str, result[0]["key"]),
            label=cast(str, result[0]["label"]),
        )
        if result
        else None
    )


def search_classification(search: str) -> Sequence[LibraryClass]:
    if not search:
        return []
    search_queries: list[str] = []
    key = ""
    parts = search.split(" ")

    # Check if the first part of the search query should be considered to be key for the library class.
    key_found = True
    for c in parts[0]:
        if not c.isdigit() and c != ".":
            key_found = False
            break
    if key_found:
        key = parts[0]
    else:
        search_queries.append(parts[0])

    search_queries.extend(parts[1:])

    sql = "SELECT id, key, label FROM classification WHERE"
    if key:
        sql += " key LIKE ?"
        if search_queries:
            sql += " OR"

    if search_queries:
        label_query = ""
        for i in range(len(search_queries)):
            if i == 0:
                label_query += " label LIKE ?"
            else:
                label_query += " OR label LIKE ?"
        sql += label_query

    params: list[str] = []
    if key:
        params.append(f"%{key}%")

    for s in search_queries:
        params.append(f"%{s}%")

    result = db.query(sql, params)

    print(result)

    classes: list[LibraryClass] = []
    for c in cast(Sequence[LibraryClassResult], result):
        classes.append(
            LibraryClass(id=c["id"], key=c["key"], label=c["label"])
        )

    return classes
