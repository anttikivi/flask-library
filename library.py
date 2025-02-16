from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import TypedDict, cast

from flask import abort

import db
import users


@dataclass
class Book:
    id: int
    isbn: str | None
    name: str
    author_id: int
    class_id: int


@dataclass
class JointBook:
    id: int
    isbn: str | None
    name: str
    author: str
    classification: str


@dataclass
class CountBook:
    id: int
    isbn: str | None
    name: str
    author: str
    classification: str
    count: int


@dataclass
class LibraryClass:
    id: int
    key: str
    label: str


@dataclass
class BookIDCounts:
    id: int
    count: int


@dataclass
class Review:
    id: int
    user: users.User
    book_id: int
    stars: int
    msg: str | None
    timestamp: datetime
    last_edited: datetime


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

IDCountResult = TypedDict("IDCountResult", {"id": int, "total": int})

CountBooksResult = TypedDict(
    "CountBooksResult",
    {
        "id": int,
        "isbn": str | None,
        "name": str,
        "author": str,
        "classification": str,
        "total": int,
    },
)


LibraryClassResult = TypedDict(
    "LibraryClassResult", {"id": int, "key": str, "label": str}
)

ReviewResult = TypedDict(
    "ReviewResult",
    {
        "id": int,
        "user_id": int,
        "username": str,
        "book_id": int,
        "stars": int,
        "message": str | None,
        "time": str,
        "last_edited": str,
    },
)


def create_library(user_id: int):
    sql = "INSERT INTO libraries (user_id) VALUES (?)"
    db.execute(sql, [user_id])


def create_book(isbn: str | None, name: str, author_id: int, class_id: int):
    sql = """
        INSERT INTO books (isbn, name, author_id, class_id)
        VALUES (?, ?, ?, ?)
    """
    db.execute(sql, [isbn, name, author_id, class_id])


def add_review(
    user_id: int, book_id: int, stars: int, message: str | None = None
):
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
    db.execute(sql, [user_id, book_id, stars, message])


def update_review(
    user_id: int, book_id: int, stars: int, message: str | None = None
):
    sql = """
        UPDATE reviews
        SET
            stars = ?,
            message = ?,
            last_edited = datetime('now')
        WHERE user_id = ? AND book_id = ?
    """
    db.execute(sql, [stars, message, user_id, book_id])


def mark_as_read(user_id: int, book_id: int):
    """
    Marks the book read by the given user.
    """
    sql = """
        INSERT INTO read_books (user_id, book_id)
        VALUES (?, ?)
    """
    db.execute(sql, [user_id, book_id])


def get_user_library(user_id: int) -> int | None:
    sql = "SELECT id FROM libraries WHERE user_id = ?"
    result = db.query(sql, [user_id])
    return result[0]["id"] if result else None


def add_book_to_user(book_id: int, user_id: int):
    sql = """
        INSERT INTO book_ownerships (book_id, library_id)
        VALUES (?, (SELECT id FROM libraries WHERE user_id = ?))
    """
    db.execute(sql, [book_id, user_id])


def update_book_name(book_id: int, new_name: str):
    sql = "UPDATE books SET name = ? WHERE id = ?"
    db.execute(sql, [new_name, book_id])


def update_book_isbn(book_id: int, new_isbn: str):
    sql = "UPDATE books SET isbn = ? WHERE id = ?"
    db.execute(sql, [new_isbn, book_id])


def update_book_author(book_id: int, new_author_id: int):
    sql = "UPDATE books SET author_id = ? WHERE id = ?"
    db.execute(sql, [new_author_id, book_id])


def update_book_class(book_id: int, new_class_id: int):
    sql = "UPDATE books SET class_id = ? WHERE id = ?"
    db.execute(sql, [new_class_id, book_id])


def remove_books_from_user(book_id: int, user_id: int, count: int = 1):
    sql = """
        DELETE FROM book_ownerships
        WHERE id IN (
            SELECT o.id
            FROM book_ownerships AS o
            JOIN libraries AS l ON o.library_id = l.id
            WHERE o.book_id = ? AND l.user_id = ?
            LIMIT ?
        )
    """
    db.execute(sql, [book_id, user_id, count])


def get_book_count() -> int:
    sql = "SELECT COUNT(id) FROM books"
    result = db.query(sql)
    return result[0]["COUNT(id)"] if result else 0


def get_books(page: int, page_size: int):
    sql = """
        SELECT
            b.id,
            b.isbn,
            b.name,
            IFNULL(a.first_name, '') || ' ' || a.surname AS author,
            c.label AS classification,
            COUNT(o.id) AS total
        FROM books AS b
        JOIN book_ownerships AS o ON b.id = o.book_id
        JOIN authors AS a ON b.author_id = a.id
        JOIN classification AS c ON b.class_id = c.id
        GROUP BY b.id
        ORDER BY
            c.key ASC,
            a.surname ASC,
            a.first_name ASC,
            b.name ASC,
            classification ASC,
            total DESC
        LIMIT ? OFFSET ?
    """
    limit = page_size
    offset = page_size * (page - 1)
    result = db.query(sql, [limit, offset])
    books: list[CountBook] = []
    for b in cast(Sequence[CountBooksResult], result):
        books.append(
            CountBook(
                id=b["id"],
                isbn=b["isbn"],
                name=b["name"],
                author=b["author"],
                classification=b["classification"],
                count=b["total"],
            )
        )

    return books


def get_book_by_id(id: int) -> Book | None:
    sql = "SELECT id, isbn, name, author_id, class_id FROM books WHERE id = ?"
    result = db.query(sql, [id])

    return (
        Book(
            id=cast(int, result[0]["id"]),
            isbn=cast(str | None, result[0]["isbn"]),
            name=cast(str, result[0]["name"]),
            author_id=cast(int, result[0]["author_id"]),
            class_id=cast(int, result[0]["class_id"]),
        )
        if result
        else None
    )


def get_book_total_owned_count(book_id: int) -> int:
    sql = "SELECT COUNT(id) AS total FROM book_ownerships WHERE book_id = ?"
    result = db.query(sql, [book_id])
    return result[0]["total"] if result else 0


def get_user_book_count(user_id: int) -> int:
    sql = """
        SELECT COUNT(DISTINCT o.book_id) AS total
        FROM book_ownerships AS o
        INNER JOIN libraries AS l ON o.library_id = l.id
        WHERE l.user_id = ?
    """
    result = db.query(sql, [user_id])
    return result[0]["total"] if result else 0


def get_user_grand_total_books(user_id: int) -> int:
    sql = """
        SELECT COUNT(o.id) AS total
        FROM book_ownerships AS o
        JOIN libraries AS l ON o.library_id = l.id
        WHERE l.user_id = ?
    """
    result = db.query(sql, [user_id])
    return result[0]["total"] if result else 0


def get_book_user_owned_count(book_id: int, user_id: int) -> int:
    sql = """
        SELECT COUNT(o.id) AS total
        FROM book_ownerships AS o
        JOIN libraries AS l ON o.library_id = l.id
        WHERE o.book_id = ? AND l.user_id = ?
    """
    result = db.query(sql, [book_id, user_id])
    return result[0]["total"] if result else 0


def get_popular_books(count: int) -> Sequence[CountBook]:
    sql = """
        SELECT
            b.id,
            b.isbn,
            b.name,
            IFNULL(a.first_name, '') || ' ' || a.surname AS author,
            c.label AS classification,
            COUNT(o.id) AS total
        FROM books AS b
        JOIN book_ownerships AS o ON b.id = o.book_id
        JOIN authors AS a ON b.author_id = a.id
        JOIN classification AS c ON b.class_id = c.id
        GROUP BY b.id
        ORDER BY total DESC, c.key ASC, author ASC, b.name ASC
        LIMIT ?
    """
    result = db.query(sql, [count])

    books: list[CountBook] = []
    for b in cast(Sequence[CountBooksResult], result):
        books.append(
            CountBook(
                id=b["id"],
                isbn=b["isbn"],
                name=b["name"],
                author=b["author"],
                classification=b["classification"],
                count=b["total"],
            )
        )

    return books


def get_owned_books(user_id: int) -> Sequence[CountBook]:
    """
    Returns the books owned by the given user.
    """
    sql = """
        SELECT
            b.id,
            b.isbn,
            b.name,
            IFNULL(a.first_name, '') || ' ' || a.surname AS author,
            c.label AS classification,
            COUNT(o.id) AS total
        FROM books AS b
        JOIN book_ownerships AS o ON b.id = o.book_id
        JOIN libraries AS l ON o.library_id = l.id
        JOIN authors AS a ON b.author_id = a.id
        JOIN classification AS c ON b.class_id = c.id
        WHERE l.user_id = ?
        ORDER BY
            c.key ASC,
            a.surname ASC,
            a.first_name ASC,
            b.name ASC,
            c.key ASC,
            c.label ASC,
            total DESC
    """

    result = db.query(sql, [user_id])

    books: list[CountBook] = []
    for b in cast(Sequence[CountBooksResult], result):
        books.append(
            CountBook(
                id=b["id"],
                isbn=b["isbn"],
                name=b["name"],
                author=b["author"],
                classification=b["classification"],
                count=b["total"],
            )
        )

    return books


def get_read_books(user_id: int) -> Sequence[JointBook]:
    """
    Returns the books read by the given user.
    """
    sql = """
        SELECT
            b.id,
            b.isbn,
            b.name,
            IFNULL(a.first_name, '') || ' ' || a.surname AS author,
            c.label AS classification
        FROM books AS b
        JOIN read_books AS r ON b.id = r.book_id
        JOIN authors AS a ON b.author_id = a.id
        JOIN classification AS c ON b.class_id = c.id
        WHERE r.user_id = ?
        ORDER BY
            c.key ASC,
            a.surname ASC,
            a.first_name ASC,
            b.name ASC,
            c.key ASC,
            c.label ASC
    """

    result = db.query(sql, [user_id])

    books: list[JointBook] = []
    for b in cast(Sequence[CountBooksResult], result):
        books.append(
            JointBook(
                id=b["id"],
                isbn=b["isbn"],
                name=b["name"],
                author=b["author"],
                classification=b["classification"],
            )
        )

    return books


def get_owned_books_paginated(
    user_id: int, page: int, page_size: int
) -> Sequence[CountBook]:
    """
    Returns the books owned by the given user.
    """
    sql = """
        SELECT
            b.id,
            b.isbn,
            b.name,
            IFNULL(a.first_name, '') || ' ' || a.surname AS author,
            c.label AS classification,
            COUNT(o.id) AS total
        FROM books AS b
        JOIN book_ownerships AS o ON b.id = o.book_id
        JOIN libraries AS l ON o.library_id = l.id
        JOIN authors AS a ON b.author_id = a.id
        JOIN classification AS c ON b.class_id = c.id
        WHERE l.user_id = ?
        GROUP BY
            b.id,
            b.isbn,
            b.name,
            author,
            classification
        ORDER BY
            c.key ASC,
            a.surname ASC,
            a.first_name ASC,
            b.name ASC,
            c.key ASC,
            c.label ASC,
            total DESC
        LIMIT ? OFFSET ?
    """
    limit = page_size
    offset = page_size * (page - 1)
    result = db.query(sql, [user_id, limit, offset])
    books: list[CountBook] = []
    for b in cast(Sequence[CountBooksResult], result):
        books.append(
            CountBook(
                id=b["id"],
                isbn=b["isbn"],
                name=b["name"],
                author=b["author"],
                classification=b["classification"],
                count=b["total"],
            )
        )

    return books


def get_owned_book_counts_by_id(user_id: int) -> Sequence[BookIDCounts]:
    """
    Returns the book IDs of the books owned by the given user.
    """
    sql = """
        SELECT b.id, COUNT(o.id) AS total
        FROM books AS b
        JOIN book_ownerships AS o ON b.id = o.book_id
        JOIN libraries AS l ON o.library_id = l.id
        WHERE l.user_id = ?
        GROUP BY b.id
    """

    result = db.query(sql, [user_id])

    books: list[BookIDCounts] = []
    for b in cast(Sequence[IDCountResult], result):
        books.append(BookIDCounts(id=b["id"], count=b["total"]))

    return books


def is_owner(user_id: int, book_id: int) -> bool:
    """
    Checks whether the given user owns a copy of the given book.
    """
    sql = """
        SELECT COUNT(o.id) AS count
        FROM book_ownerships AS o, libraries AS l
        WHERE o.library_id = l.id AND l.user_id = ? AND o.book_id = ?
    """
    result = db.query(sql, [user_id, book_id])

    return result[0]["count"] > 0 if result else False


def is_read(user_id: int, book_id: int) -> bool:
    """
    Returns whether the given use has read the book.
    """
    sql = """
        SELECT EXISTS(
            SELECT 1
            FROM read_books
            WHERE user_id = ? AND book_id = ?
        ) AS result
    """
    result = db.query(sql, [user_id, book_id])

    return cast(int, result[0]["result"]) == 1


def search_books_from_author(author_id: int, book_name: str):
    sql = """
        SELECT id, isbn, name, author_id, class_id
        FROM books
        WHERE author_id = ? AND name LIKE ?
    """
    result = db.query(sql, [author_id, f"%{book_name}%"])

    books: list[Book] = []
    for book in cast(Sequence[BooksResult], result):
        books.append(
            Book(
                id=book["id"],
                isbn=book["isbn"],
                name=book["name"],
                author_id=book["author_id"],
                class_id=book["class_id"],
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

    classes: list[LibraryClass] = []
    for c in cast(Sequence[LibraryClassResult], result):
        classes.append(
            LibraryClass(id=c["id"], key=c["key"], label=c["label"])
        )

    return classes


def search(
    page: int,
    page_size: int,
    isbn: str | None,
    name: str | None,
    author: str | None,
    classification: str | None,
):
    sql = """
        SELECT
            b.id,
            b.isbn,
            b.name,
            IFNULL(a.first_name, '') || ' ' || a.surname AS author,
            c.label AS classification,
            COUNT(o.id) AS total
        FROM books AS b
        JOIN book_ownerships AS o ON b.id = o.book_id
        JOIN authors AS a ON b.author_id = a.id
        JOIN classification AS c ON b.class_id = c.id
    """

    if isbn or name or author or classification:
        sql += "WHERE "

    query: list[str] = []
    params: list[str | int] = []
    if isbn:
        query.append("b.isbn LIKE ?")
        params.append(f"%{isbn}%")

    if name:
        query.append("b.name LIKE ?")
        params.append(f"%{name}%")

    if author:
        parts = author.split()
        for p in parts:
            query.append("(a.first_name LIKE ? OR a.surname LIKE ?)")
            params.append(p)
            params.append(p)

    if classification:
        parts = classification.split()
        for p in parts:
            query.append("(c.key LIKE ? OR c.label LIKE ?)")
            params.append(p)
            params.append(p)

    sql += (
        " AND ".join(query)
        + """GROUP BY b.id
        ORDER BY
            c.key ASC,
            a.surname ASC,
            a.first_name ASC,
            b.name ASC,
            classification ASC,
            total DESC
        LIMIT ? OFFSET ?
    """
    )
    limit = page_size
    offset = page_size * (page - 1)
    params.append(limit)
    params.append(offset)
    result = db.query(sql, params)
    books: list[CountBook] = []
    for b in cast(Sequence[CountBooksResult], result):
        books.append(
            CountBook(
                id=b["id"],
                isbn=b["isbn"],
                name=b["name"],
                author=b["author"],
                classification=b["classification"],
                count=b["total"],
            )
        )

    return books


def search_result_count(
    isbn: str | None,
    name: str | None,
    author: str | None,
    classification: str | None,
) -> int:
    sql = """
        SELECT COUNT(b.id)
        FROM books AS b
        JOIN authors AS a ON b.author_id = a.id
        JOIN classification AS c ON b.class_id = c.id
    """

    if isbn or name or author or classification:
        sql += "WHERE "

    query: list[str] = []
    params: list[str | int] = []
    if isbn:
        query.append("b.isbn LIKE ?")
        params.append(f"%{isbn}%")

    if name:
        query.append("b.name LIKE ?")
        params.append(f"%{name}%")

    if author:
        parts = author.split()
        for p in parts:
            query.append("(a.first_name LIKE ? OR a.surname LIKE ?)")
            params.append(p)
            params.append(p)

    if classification:
        parts = classification.split()
        for p in parts:
            query.append("(c.key LIKE ? OR c.label LIKE ?)")
            params.append(p)
            params.append(p)

    sql += " AND ".join(query)
    result = db.query(sql, params)

    return result[0]["COUNT(b.id)"] if result else 0


def get_reviews(book_id: int) -> Sequence[Review]:
    """
    Returns the reviews for a book.
    """
    sql = """
        SELECT
            r.id,
            r.user_id,
            u.username AS username,
            r.book_id,
            r.stars,
            r.message,
            r.time,
            r.last_edited
        FROM reviews AS r
        JOIN users AS u ON u.id = r.user_id
        JOIN books AS b ON b.id = r.book_id
        WHERE r.book_id = ?
        ORDER BY r.time
    """
    result = db.query(sql, [book_id])

    reviews: list[Review] = []
    for r in cast(Sequence[ReviewResult], result):
        try:
            reviews.append(
                Review(
                    id=r["id"],
                    user=users.User(id=r["user_id"], username=r["username"]),
                    book_id=r["book_id"],
                    stars=r["stars"],
                    msg=r["message"],
                    timestamp=datetime.strptime(
                        r["time"], "%Y-%m-%d %H:%M:%S"
                    ),
                    last_edited=datetime.strptime(
                        r["last_edited"], "%Y-%m-%d %H:%M:%S"
                    ),
                )
            )
        except ValueError:
            print("Invalid time format found in the database")
            abort(500)

    return reviews


def get_user_review(book_id: int, user_id: int) -> Review | None:
    """
    Returns the reviews for a book.
    """
    sql = """
        SELECT
            r.id,
            r.user_id,
            u.username AS username,
            r.book_id,
            r.stars,
            r.message,
            r.time,
            r.last_edited
        FROM reviews AS r
        JOIN users AS u ON u.id = r.user_id
        JOIN books AS b ON b.id = r.book_id
        WHERE r.book_id = ? AND r.user_id = ?
    """
    result = db.query(sql, [book_id, user_id])

    review: Review | None = None
    if result:
        r = cast(ReviewResult, result[0])
        try:
            review = Review(
                id=r["id"],
                user=users.User(id=r["user_id"], username=r["username"]),
                book_id=r["book_id"],
                stars=r["stars"],
                msg=r["message"],
                timestamp=datetime.strptime(r["time"], "%Y-%m-%d %H:%M:%S"),
                last_edited=datetime.strptime(
                    r["last_edited"], "%Y-%m-%d %H:%M:%S"
                ),
            )
        except ValueError:
            print("Invalid time format found in the database")
            abort(500)

    return review


def has_left_review(user_id: int, book_id: int) -> bool:
    """
    Returns whether the given use has left a review for the given book.
    """
    sql = """
        SELECT EXISTS(
            SELECT 1
            FROM reviews
            WHERE user_id = ? AND book_id = ?
        ) AS result
    """
    result = db.query(sql, [user_id, book_id])

    return cast(int, result[0]["result"]) == 1
