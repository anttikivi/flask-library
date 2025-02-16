import locale
import math
import os
import secrets
from collections.abc import Mapping, Sequence
from typing import cast

from flask import (
    Flask,
    abort,
    flash,
    redirect,
    render_template,
    request,
    session,
)
from werkzeug.wrappers import Response

import add_book
import author
import checks
import db
import env
import library
import users

env.read_env_file()

app = Flask(__name__)
app.secret_key = os.environ["SECRET_KEY"]

context = {"site": {"subtitle": "Kirjat purkissa", "title": "Flask-kirjasto"}}


@app.route("/", methods=["GET"])
def index() -> str:
    books = library.get_popular_books(10)
    owned: Sequence[library.BookIDCounts] = []
    read_books: Sequence[library.JointBook] = []
    if "user_id" in session:
        owned = library.get_owned_book_counts_by_id(
            cast(int, session["user_id"])
        )
        read_books = library.get_read_books(cast(int, session["user_id"]))
    return render_template(
        "index.html",
        books=books,
        owned=owned,
        read_books=read_books,
        is_home=True,
        **context,
    )


########################################################################
# USER MANAGEMENT
########################################################################


@app.route(
    "/kayttaja/<string:username>/", defaults={"page": None}, methods=["GET"]
)
@app.route("/kayttaja/<string:username>/<int:page>/", methods=["GET"])
def user_page(username: str, page: int | None):
    user = users.get_users_by_name(username)
    if not user:
        abort(404)

    per_page = request.args.get("per_page")
    book_count = library.get_user_book_count(user.id)
    print("Book count", book_count)
    page_size = 10
    if per_page:
        page_size = int(per_page)

    page_count = math.ceil(book_count / page_size) if book_count > 0 else 1

    add_per_page_param = False

    params: str = ""
    if per_page:
        params = f"?per_page={per_page}"
        add_per_page_param = True

    if (page and page <= 1) or "reset_page" in request.args:
        # I want the default URL to be clean.
        return redirect(f"/kayttaja/{username}/{params}")

    # Set the correct page after checking for the redirection so that we
    # don't get infinite loop.
    if not page or page <= 1:
        page = 1

    if page > page_count:
        return redirect(f"/kayttaja/{username}/{page_count}{params}")

    books = library.get_owned_books_paginated(user.id, page, page_size)
    owned: Sequence[library.BookIDCounts] = []
    owned = library.get_owned_book_counts_by_id(user.id)
    read_books: Sequence[library.JointBook] = []
    if "user_id" in session:
        read_books = library.get_read_books(cast(int, session["user_id"]))

    grand_total = library.get_user_grand_total_books(user.id)

    return render_template(
        "user.html",
        user=user,
        grand_total=grand_total,
        books=books,
        page=page,
        page_count=page_count,
        page_size=page_size,
        add_per_page_param=add_per_page_param,
        owned=owned,
        read_books=read_books,
        **context,
    )


@app.route("/asetukset/", methods=["GET", "POST"])
def edit_user():
    if "username" not in session:
        abort(401)

    username: str = session["username"]

    user = users.get_users_by_name(username)
    if not user:
        # The session has a username so we can expect to find the user
        # in the database.
        abort(500)

    if request.method == "POST":
        checks.check_csrf()

        if "what" not in request.form:
            abort(400)
        what = request.form["what"]
        if what != "username" and what != "password":
            abort(400)

        if what == "username":
            new_username = request.form["username"]
            password = request.form["password"]
            form_data = {"username": new_username}
            if not users.is_valid_username(new_username):
                flash(
                    "Käyttäjätunnus saa sisältää vain kirjaimia ja numeroita sekä yhdysmerkkejä ja alaviivoja. Se ei saa sisältää ääkkösiä. Käyttäjätunnuksen enimmäispituus on 16 merkkiä",
                    "username",
                )
                return render_template(
                    "user_settings.html",
                    form_data=form_data,
                    user=user,
                    **context,
                )
            check_user = users.get_users_by_name(new_username)
            if check_user:
                flash("Käyttäjätunnus on varattu", "username")
                return render_template(
                    "user_settings.html",
                    form_data=form_data,
                    user=user,
                    **context,
                )

            user_id = users.check_login(username, password)
            if not user_id:
                flash("Väärä salasana", "username")
                return render_template(
                    "user_settings.html",
                    form_data=form_data,
                    user=user,
                    **context,
                )

            users.change_username(user_id, new_username)
            new_user = users.get_users_by_name(new_username)

            if new_user is None:
                abort(500)

            if user_id:
                session["user_id"] = new_user.id
                session["username"] = new_user.username
                session["csrf_token"] = secrets.token_hex(16)
                return render_template(
                    "user_settings.html", user=new_user, **context
                )

        if what == "password":
            old_password = request.form["old_password"]
            new_password = request.form["new_password"]
            new_password_again = request.form["new_password_again"]
            if new_password != new_password_again:
                flash("Salasanat eivät täsmää", "password")
                return render_template(
                    "user_settings.html", user=user, **context
                )

            user_id = users.check_login(username, old_password)
            if not user_id:
                flash("Väärä salasana", "password")
                return render_template(
                    "user_settings.html", user=user, **context
                )

            users.change_password(user_id, new_password)

            # These checks might not really be necessary, but it's fast
            # enough and I think it's reasonable to also reset the CSRF token.
            new_user = users.get_users_by_name(username)
            if new_user is None:
                abort(500)

            if user_id:
                session["user_id"] = new_user.id
                session["username"] = new_user.username
                session["csrf_token"] = secrets.token_hex(16)
                return render_template(
                    "user_settings.html", user=new_user, **context
                )

    return render_template("user_settings.html", user=user, **context)


@app.route("/luo-tili/", methods=["GET", "POST"])
def register() -> str | Response:
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        password_again = request.form["password_again"]
        form_data = {"username": username}

        next_page = (
            request.form["next-page"]
            if "next-page" in request.form
            else "/" + username + "/"
        )

        if request.args.get("next"):
            next_page = cast(str, request.args.get("next"))

        if not users.is_valid_username(username):
            flash(
                "Käyttäjätunnus saa sisältää vain kirjaimia ja numeroita sekä yhdysmerkkejä ja alaviivoja. Se ei saa sisältää ääkkösiä. Käyttäjätunnuksen enimmäispituus on 16 merkkiä",
                "error",
            )
            return render_template(
                "register.html",
                form_data=form_data,
                next_page=next_page,
                **context,
            )

        if password != password_again:
            flash("Salasanat eivät täsmää", "error")
            return render_template(
                "register.html",
                form_data=form_data,
                next_page=next_page,
                **context,
            )

        if users.get_users_by_name(username):
            flash("Käyttäjätunnus on jo varattu", "error")
            return render_template(
                "register.html",
                form_data=form_data,
                next_page=next_page,
                **context,
            )

        # Because I check the username's uniqueness above, there is no
        # need to check for error here: if the database operation fails,
        # it is desirable to return an internal server error as that
        # tells me that there is really a bug in the program. I try to
        # stay away from using excetion for flow control.
        users.create_user(username, password)

        # Log in the user.
        user_id = users.check_login(username, password)
        if user_id:
            # Each user has exactly one library, and it is created
            # during the registration.
            library.create_library(user_id)

            session["user_id"] = user_id
            session["username"] = username
            session["csrf_token"] = secrets.token_hex(16)

            return redirect(next_page)

        # If we cannot log in the user we just created, something is wrong.
        abort(500)

    # If the method is not "POST", I can assume it's "GET" (might also
    # be "HEAD" or "OPTIONS", but Flask takes care of those for us).
    return render_template(
        "register.html", next_page=request.referrer, **context
    )


@app.route("/kirjaudu/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        form_data = {"username": username}

        next_page = (
            request.form["next-page"]
            if "next-page" in request.form
            else "/" + username + "/"
        )

        user_id = users.check_login(username, password)
        if user_id:
            session["user_id"] = user_id
            session["username"] = username
            session["csrf_token"] = secrets.token_hex(16)

            return redirect(next_page)

        flash("Väärä käyttäjätunnus tai salasana", "error")
        return render_template(
            "login.html", form_data=form_data, next_page=next_page, **context
        )

    # If the method is not "POST", it's "GET".
    return render_template("login.html", next_page=request.referrer, **context)


@app.route("/logout/", methods=["GET"])
def logout() -> Response:
    if "user_id" in session:
        del session["user_id"]
        del session["username"]
    if not request.referrer:
        # If there is no referrer (e.g. /logout/ was called by typing
        # address to the browser, redirect to the home page to avoid a
        # 404 error by address "/logout/None").
        return redirect("/")
    # TODO: Is using the referrer here the best solution? At least for
    # now it helps catching any routes that user might be able to access
    # without logging in.
    return redirect(request.referrer)


########################################################################
# LIBRARY PAGES
########################################################################


@app.route("/kirjasto/", defaults={"page": None}, methods=["GET"])
@app.route("/kirjasto/<int:page>/", methods=["GET"])
def library_page(page: int | None):
    per_page = request.args.get("per_page")
    book_count = library.get_book_count()
    page_size = 10
    if per_page:
        page_size = int(per_page)

    # Page count needs to be at least 1 to display the library page with
    # no books.
    page_count = math.ceil(book_count / page_size) if book_count > 0 else 1

    add_per_page_param = False

    params: str = ""
    if per_page:
        params = f"?per_page={per_page}"
        add_per_page_param = True

    if (page and page <= 1) or "reset_page" in request.args:
        # I want the default URL to be clean.
        return redirect(f"/kirjasto{params}")

    # Set the correct page after checking for the redirection so that we
    # don't get infinite loop.
    if not page or page <= 1:
        page = 1

    if page > page_count:
        return redirect(f"/kirjasto/{page_count}{params}")

    books = library.get_books(page, page_size)
    owned: Sequence[library.BookIDCounts] = []
    read_books: Sequence[library.JointBook] = []
    if "user_id" in session:
        owned = library.get_owned_book_counts_by_id(
            cast(int, session["user_id"])
        )
        read_books = library.get_read_books(cast(int, session["user_id"]))

    return render_template(
        "library.html",
        books=books,
        page=page,
        page_count=page_count,
        page_size=page_size,
        add_per_page_param=add_per_page_param,
        owned=owned,
        read_books=read_books,
        **context,
    )


@app.route("/kirjasto/haku/", defaults={"page": None}, methods=["GET", "POST"])
@app.route("/kirjasto/haku/<int:page>/", methods=["GET", "POST"])
def library_search(page: int | None):
    isbn = ""
    name = ""
    author = ""
    classification = ""
    if request.args.get("isbn"):
        isbn = str(request.args.get("isbn"))
    if request.args.get("name"):
        name = str(request.args.get("name"))
    if request.args.get("author"):
        author = str(request.args.get("author"))
    if request.args.get("classification"):
        classification = str(request.args.get("classification"))

    # NOTE: We want to keep the state of the search in the URL, but with
    # a new post, override the URL parameters.
    if request.method == "POST":
        if "isbn" in request.form:
            isbn = request.form["isbn"]
        if "name" in request.form:
            name = request.form["name"]
        if "author" in request.form:
            author = request.form["author"]
        if "classification" in request.form:
            classification = request.form["classification"]

    per_page = request.args.get("per_page")
    book_count = library.search_result_count(
        isbn=isbn, name=name, author=author, classification=classification
    )
    page_size = 10
    if per_page:
        page_size = int(per_page)

    page_count = math.ceil(book_count / page_size) if book_count > 0 else 1

    add_per_page_param = False

    params: str = ""
    if per_page:
        params = f"?per_page={per_page}"
        add_per_page_param = True

    if isbn:
        params += f"&isbn={isbn}" if params else f"?isbn={isbn}"
    if name:
        params += f"&name={name}" if params else f"?name={name}"
    if author:
        params += f"&author={author}" if params else f"?author={author}"
    if classification:
        params += (
            f"&classification={classification}"
            if params
            else f"?classification={classification}"
        )

    if (page and page <= 1) or "reset_page" in request.args:
        # I want the default URL to be clean.
        return redirect(f"/kirjasto/haku{params}")

    # Set the correct page after checking for the redirection so that we
    # don't get infinite loop.
    if not page or page <= 1:
        page = 1

    if page > page_count:
        return redirect(f"/kirjasto/haku/{page_count}{params}")

    if request.method == "POST":
        return redirect(f"/kirjasto/haku{params}")

    books = library.search(
        page=page,
        page_size=page_size,
        isbn=isbn,
        name=name,
        author=author,
        classification=classification,
    )

    owned: Sequence[library.BookIDCounts] = []
    read_books: Sequence[library.JointBook] = []
    if "user_id" in session:
        owned = library.get_owned_book_counts_by_id(
            cast(int, session["user_id"])
        )
        read_books = library.get_read_books(cast(int, session["user_id"]))

    search_params = params[1:]

    form_data = {
        "isbn": isbn,
        "name": name,
        "author": author,
        "classification": classification,
    }

    return render_template(
        "library_search.html",
        books=books,
        page=page,
        page_count=page_count,
        page_size=page_size,
        add_per_page_param=add_per_page_param,
        owned=owned,
        search_params=search_params,
        form_data=form_data,
        read_books=read_books,
        **context,
    )


########################################################################
# BOOK MANAGEMENT
########################################################################


@app.route("/lisaa-kirja/", methods=["GET", "POST"])
def add_book_page() -> str | Response:
    return add_book.render_page(**context)


@app.route("/kirja/<int:book_id>", methods=["GET"])
def book_page(book_id: int):
    book = library.get_book_by_id(book_id)
    if not book:
        abort(404)
    book_author = author.get_author_by_id(book.author_id)
    if not book_author:
        abort(500)
    book_class = library.get_classification_by_id(book.class_id)
    if not book_class:
        abort(500)

    owns = (
        library.is_owner(cast(int, session["user_id"]), book_id)
        if "user_id" in session
        else False
    )
    count = library.get_book_total_owned_count(book_id)
    owned_count = (
        library.get_book_user_owned_count(
            book_id, cast(int, session["user_id"])
        )
        if "user_id" in session
        else 0
    )
    is_read = (
        library.is_read(cast(int, session["user_id"]), book_id)
        if "user_id" in session
        else False
    )
    reviews = library.get_reviews(book_id)
    has_left_review = (
        library.has_left_review(cast(int, session["user_id"]), book_id)
        if "user_id" in session
        else False
    )
    fmt_times: Mapping[int, str] = {}
    _ = locale.setlocale(locale.LC_TIME, "fi_FI")
    for r in reviews:
        fmt_times[r.id] = r.timestamp.strftime("%A %d.%m.%Y klo %H.%M")
    return render_template(
        "book.html",
        author=book_author,
        book=book,
        book_class=book_class,
        owns=owns,
        count=count,
        owned_count=owned_count,
        has_read=is_read,
        reviews=reviews,
        has_left_review=has_left_review,
        fmt_times=fmt_times,
        **context,
    )


@app.route("/kirja/<int:book_id>/muokkaa/", methods=["GET", "POST"])
def edit_book(book_id: int):
    checks.check_login()

    book = library.get_book_by_id(book_id)
    if not book:
        abort(404)
    book_author = author.get_author_by_id(book.author_id)
    if not book_author:
        abort(500)
    book_class = library.get_classification_by_id(book.class_id)
    if not book_class:
        abort(500)

    owns = (
        library.is_owner(cast(int, session["user_id"]), book_id)
        if "user_id" in session
        else False
    )

    if not owns:
        abort(403)

    if request.method == "POST":
        checks.check_csrf()

        if "what" not in request.form:
            abort(400)
        what = request.form["what"]
        if (
            what != "name"
            and what != "isbn"
            and what != "author"
            and what != "author-update"
        ):
            abort(400)

        if what == "name":
            new_name = request.form["name"]
            if not new_name:
                flash("Sinun tulee antaa nimi", "name")
                return render_template(
                    "edit_book.html",
                    book=book,
                    author=book_author,
                    book_class=book_class,
                    **context,
                )

            library.update_book_name(book_id, new_name)
            book = library.get_book_by_id(book_id)
            if not book:
                abort(500)
            book_author = author.get_author_by_id(book.author_id)
            if not book_author:
                abort(500)
            book_class = library.get_classification_by_id(book.class_id)
            if not book_class:
                abort(500)

        if what == "isbn":
            new_isbn = request.form["isbn"]
            if not new_isbn:
                flash("Sinun tulee antaa ISBN-tunnus", "isbn")
                return render_template(
                    "edit_book.html",
                    book=book,
                    author=book_author,
                    book_class=book_class,
                    **context,
                )

            library.update_book_isbn(book_id, new_isbn)
            book = library.get_book_by_id(book_id)
            if not book:
                abort(500)
            book_author = author.get_author_by_id(book.author_id)
            if not book_author:
                abort(500)
            book_class = library.get_classification_by_id(book.class_id)
            if not book_class:
                abort(500)

        if what == "author":
            first_name = request.form["first-name-search"]
            if (
                "surname-search" not in request.form
                or not request.form["surname-search"]
            ):
                flash("Anna sukunimi tai nimimerkki", "author")
                form_data = {"author": {"first_name": first_name}}
                return render_template(
                    "edit_book.html",
                    form_data=form_data,
                    book=book,
                    author=book_author,
                    book_class=book_class,
                    **context,
                )
            surname = request.form["surname-search"]
            authors: Sequence[author.Author] = []
            author_match = author.get_author(
                request.form["first-name-search"],
                request.form["surname-search"],
            )
            if author_match:
                authors.append(author_match)

            if not authors:
                authors = author.seach_author(
                    request.form["first-name-search"],
                    request.form["surname-search"],
                )
            form_data = {
                "author": {"first_name": first_name, "surname": surname}
            }
            return render_template(
                "edit_book.html",
                form_data=form_data,
                book=book,
                author=book_author,
                book_class=book_class,
                authors=authors,
                author_results=True,
                **context,
            )

        if what == "author-update":
            if "selected-form" not in request.form:
                abort(400)

            selected_form = request.form["selected-form"]
            if selected_form == "select-author":
                if "author" not in request.form or not request.form["author"]:
                    flash(
                        "Sinun tulee valita kirjoittaja tai luoda uusi",
                        "author",
                    )
                    first_name = request.form["last-first-name"]
                    surname = request.form["last-surname"]
                    authors = []
                    author_match = author.get_author(first_name, surname)
                    if author_match:
                        authors.append(author_match)

                    if not authors:
                        authors = author.seach_author(first_name, surname)
                    form_data = {
                        "author": {
                            "first_name": first_name,
                            "surname": surname,
                        }
                    }
                    return render_template(
                        "add_book.html",
                        form_data=form_data,
                        book=book,
                        author=book_author,
                        book_class=book_class,
                        authors=authors,
                        author_results=True,
                        **context,
                    )
                author_id = int(request.form["author"])
                selected = author.get_author_by_id(author_id)
                if not selected:
                    abort(500)
                library.update_book_author(
                    book_id=book_id, new_author_id=selected.id
                )
                return redirect(f"/kirja/{book_id}/muokkaa")
            elif selected_form == "new-author":
                first_name = request.form["first-name"]
                if (
                    "surname" not in request.form
                    or not request.form["surname"]
                ):
                    flash("Anna sukunimi tai nimimerkki", "author")
                    first_name = request.form["first-name"]
                    surname = ""
                    authors = []
                    author_match = author.get_author(first_name, surname)
                    if author_match:
                        authors.append(author_match)

                    if not authors:
                        authors = author.seach_author(first_name, surname)
                    form_data = {
                        "author": {
                            "first_name": first_name,
                            "surname": surname,
                        }
                    }
                    return render_template(
                        "add_book.html",
                        form_data=form_data,
                        book=book,
                        author=book_author,
                        book_class=book_class,
                        authors=authors,
                        author_results=True,
                        **context,
                    )

                surname = request.form["surname"]
                author.create_author(first_name, surname)
                created = author.get_author_by_id(db.last_insert_id())
                if not created:
                    abort(500)
                library.update_book_author(
                    book_id=book_id, new_author_id=created.id
                )
                return redirect(f"/kirja/{book_id}/muokkaa")
            else:
                abort(400)

    return render_template(
        "edit_book.html",
        book=book,
        author=book_author,
        book_class=book_class,
        **context,
    )


@app.route("/kirja/<int:book_id>/muokkaa-luokitusta/", methods=["GET", "POST"])
def edit_book_classification(book_id: int):
    checks.check_login()

    book = library.get_book_by_id(book_id)
    if not book:
        abort(404)
    book_author = author.get_author_by_id(book.author_id)
    if not book_author:
        abort(500)
    book_class = library.get_classification_by_id(book.class_id)
    if not book_class:
        abort(500)

    owns = (
        library.is_owner(cast(int, session["user_id"]), book_id)
        if "user_id" in session
        else False
    )

    if not owns:
        abort(403)

    if request.method == "POST":
        checks.check_csrf()

        if "what" not in request.form:
            abort(400)
        what = request.form["what"]
        if what != "search" and what != "select":
            abort(400)

        if what == "search":
            search = request.form["class-search"]
            if not search:
                flash("Anna luokituksen haku", "classification")
                return render_template(
                    "edit_book_classification.html",
                    book=book,
                    author=book_author,
                    book_class=book_class,
                    **context,
                )
            new_classes = library.search_classification(search)
            form_data = {"last_class_search": search}
            return render_template(
                "edit_book_classification.html",
                form_data=form_data,
                book=book,
                author=book_author,
                book_class=book_class,
                new_classes=new_classes,
                **context,
            )

        if what == "select":
            search = request.form["last-class-search"]
            new_class = (
                int(request.form["class"]) if "class" in request.form else 0
            )
            if not new_class:
                flash("Valitse luokitus", "classification")
                new_classes = library.search_classification(search)
                form_data = {"last_class_search": search}
                return render_template(
                    "edit_book_classification.html",
                    form_data=form_data,
                    book=book,
                    author=book_author,
                    book_class=book_class,
                    new_classes=new_classes,
                    **context,
                )

            selected_class = library.get_classification_by_id(new_class)
            if not selected_class:
                abort(400)
            library.update_book_class(book_id, selected_class.id)
            book = library.get_book_by_id(book_id)
            if not book:
                abort(404)
            book_author = author.get_author_by_id(book.author_id)
            if not book_author:
                abort(500)
            book_class = library.get_classification_by_id(book.class_id)
            if not book_class:
                abort(500)

            owns = (
                library.is_owner(cast(int, session["user_id"]), book_id)
                if "user_id" in session
                else False
            )

            if not owns:
                abort(500)

    return render_template(
        "edit_book_classification.html",
        book=book,
        author=book_author,
        book_class=book_class,
        **context,
    )


@app.route("/kirja/<int:book_id>/muokkaa-arvostelua/", methods=["GET"])
def edit_review(book_id: int):
    checks.check_login()
    book = library.get_book_by_id(book_id)
    if not book:
        abort(404)

    review = library.get_user_review(book.id, cast(int, session["user_id"]))
    if not review:
        abort(404)
    _ = locale.setlocale(locale.LC_TIME, "fi_FI")
    fmt_time: str = review.timestamp.strftime("%A %d.%m.%Y klo %H.%M")
    fmt_last_edited: str = review.last_edited.strftime("%A %d.%m.%Y klo %H.%M")
    return render_template(
        "edit_review.html",
        book=book,
        review=review,
        fmt_time=fmt_time,
        fmt_last_edited=fmt_last_edited,
        **context,
    )


@app.route("/add-one-book/", methods=["GET"])
def add_one_book():
    checks.check_csrf_from_param()
    checks.check_login()

    book_id = request.args.get("id")
    user_id = cast(int, session["user_id"])
    if not book_id or not user_id:
        abort(400)

    library.add_book_to_user(int(book_id), user_id)

    return redirect(request.referrer)


@app.route("/delete-one-book/", methods=["GET"])
def delete_one_book():
    checks.check_csrf_from_param()
    checks.check_login()

    book_id = request.args.get("id")
    user_id = cast(int, session["user_id"])
    if not book_id or not user_id:
        abort(400)

    library.remove_books_from_user(int(book_id), user_id, 1)

    return redirect(request.referrer)


@app.route("/mark-as-read/", methods=["GET"])
def mark_as_read():
    checks.check_csrf_from_param()
    checks.check_login()

    book_id = request.args.get("id")
    user_id = cast(int, session["user_id"])
    if not book_id or not user_id:
        abort(400)

    library.mark_as_read(user_id, int(book_id))

    return redirect(request.referrer)


@app.route("/add-review/", methods=["POST"])
def add_review():
    checks.check_csrf()
    checks.check_login()

    book_id = request.args.get("id")
    user_id = cast(int, session["user_id"])
    if not book_id or not user_id:
        abort(400)

    if library.get_user_review(int(book_id), user_id):
        abort(400)

    stars: int | None = (
        int(request.form["stars"]) if "stars" in request.form else None
    )
    if not stars:
        flash("Sinun tulee antaa tähtien määrä", "error")
        return redirect(f"/kirja/{int(book_id)}")

    message: str | None = (
        request.form["message"] if "message" in request.form else None
    )
    library.add_review(user_id, int(book_id), stars, message)

    return redirect(request.referrer)


@app.route("/update-review/", methods=["POST"])
def update_review():
    checks.check_csrf()
    checks.check_login()

    book_id = request.args.get("id")
    user_id = cast(int, session["user_id"])
    if not book_id or not user_id:
        abort(400)

    if not library.get_user_review(int(book_id), user_id):
        abort(400)

    stars: int | None = (
        int(request.form["stars"]) if "stars" in request.form else None
    )
    if not stars:
        flash("Sinun tulee antaa tähtien määrä", "error")
        return redirect(f"/kirja/{int(book_id)}")

    message: str | None = (
        request.form["message"] if "message" in request.form else None
    )
    library.update_review(user_id, int(book_id), stars, message)

    return redirect(f"/kirja/{book_id}")


@app.errorhandler(401)
def handle_unauthorized(_: object):
    return render_template("401.html", **context), 401


@app.errorhandler(403)
def handle_not_forbidden(_: object):
    return render_template("403.html", **context), 403


@app.errorhandler(404)
def handle_not_found(_: object):
    return render_template("404.html", **context), 404


@app.errorhandler(500)
def handle_internal_server_error(_: object):
    return render_template("500.html", **context), 500
