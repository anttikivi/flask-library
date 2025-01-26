from collections.abc import Sequence
import os
import secrets
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

import author
import db
import env
import library
import users

env.read_env_file()

app = Flask(__name__)
app.secret_key = os.environ["SECRET_KEY"]

context = {"site": {"subtitle": "Kirjat purkissa", "title": "Flask-kirjasto"}}


def check_csrf():
    if "csrf_token" not in request.form:
        abort(403)
    if request.form["csrf_token"] != session["csrf_token"]:
        abort(403)


@app.route("/", methods=["GET"])
def index() -> str:
    return render_template("index.html", **context, is_home=True)


########################################################################
# USER MANAGEMENT
########################################################################


@app.route("/kayttaja/<string:username>", methods=["GET"])
def user_page(username: str):
    user = users.get_users_by_name(username)
    if not user:
        abort(404)
    return render_template("user.html", user=user, **context)


@app.route("/asetukset/", methods=["GET", "POST"])
def edit_user():
    username: str = session["username"]
    if "username" not in session:
        abort(401)

    user = users.get_users_by_name(username)
    if not user:
        # The session has a username so we can expect to find the user
        # in the database.
        abort(500)

    if request.method == "POST":
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

        if not users.is_valid_username(username):
            flash(
                "Käyttäjätunnus saa sisältää vain kirjaimia ja numeroita sekä yhdysmerkkejä ja alaviivoja. Se ei saa sisältää ääkkösiä. Käyttäjätunnuksen enimmäispituus on 16 merkkiä",
                "error",
            )
            return render_template(
                "register.html", form_data=form_data, **context
            )

        if password != password_again:
            flash("Salasanat eivät täsmää", "error")
            return render_template(
                "register.html", form_data=form_data, **context
            )

        if users.get_users_by_name(username):
            flash("Käyttäjätunnus on jo varattu", "error")
            return render_template(
                "register.html", form_data=form_data, **context
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

            # TODO: Redirect to the user page.
            return redirect("/")

        # If we cannot log in the user we just created, something is wrong.
        abort(500)

    # If the method is not "POST", I can assume it's "GET" (might also
    # be "HEAD" or "OPTIONS", but Flask takes care of those for us).
    return render_template("register.html", **context)


@app.route("/kirjaudu/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        form_data = {"username": username}

        user_id = users.check_login(username, password)
        if user_id:
            session["user_id"] = user_id
            session["username"] = username
            session["csrf_token"] = secrets.token_hex(16)

            # TODO: Redirect to the user page.
            return redirect("/")

        flash("Väärä käyttäjätunnus tai salasana", "error")
        return render_template("login.html", form_data=form_data, **context)

    # If the method is not "POST", it's "GET".
    return render_template("login.html", **context)


@app.route("/logout/", methods=["GET"])
def logout() -> Response:
    if "user_id" in session:
        del session["user_id"]
        del session["username"]
    return redirect("/")


########################################################################
# BOOK MANAGEMENT
########################################################################


@app.route("/lisaa-kirja/", methods=["GET", "POST"])
def add_book() -> str | Response:
    # Regardless of method, unauthenticated users cannot access this
    # page.
    if "user_id" not in session:
        abort(401)

    if request.method == "POST":
        check_csrf()

        if not request.form or "from-page" not in request.form:
            abort(400)
        from_page = int(request.form["from-page"])

        # Handling the route is done as per the form page we are coming
        # from.
        if from_page == 0:
            first_name = request.form["first-name-search"]
            if (
                "surname-search" not in request.form
                or not request.form["surname-search"]
            ):
                flash("Anna sukunimi tai nimimerkki", "error")
                form_data = {"page": from_page, "first_name": first_name}
                return render_template(
                    "add_book.html", form_data=form_data, **context
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
                "page": from_page + 1,
                "first_name": first_name,
                "surname": surname,
            }
            return render_template(
                "add_book.html",
                authors=authors,
                form_data=form_data,
                **context,
            )

        if from_page == 1:
            if "selected-form" not in request.form:
                abort(400)

            selected_form = request.form["selected-form"]
            if selected_form == "select-author":
                if "author" not in request.form or not request.form["author"]:
                    flash(
                        "Sinun tulee valita kirjoittaja tai luoda uusi",
                        "error",
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
                        "page": from_page,
                        "first_name": first_name,
                        "surname": surname,
                    }
                    return render_template(
                        "add_book.html",
                        authors=authors,
                        form_data=form_data,
                        **context,
                    )
                author_id = int(request.form["author"])
                selected = author.get_author_by_id(author_id)
                form_data = {"page": from_page + 1}
                return render_template(
                    "add_book.html",
                    author=selected,
                    form_data=form_data,
                    **context,
                )
            elif selected_form == "new-author":
                first_name = request.form["first-name"]
                if (
                    "surname" not in request.form
                    or not request.form["surname"]
                ):
                    flash("Anna sukunimi tai nimimerkki", "error")
                    first_name = request.form["first-name"]
                    surname = request.form["surname"]
                    authors = []
                    author_match = author.get_author(first_name, surname)
                    if author_match:
                        authors.append(author_match)

                    if not authors:
                        authors = author.seach_author(first_name, surname)
                    form_data = {
                        "page": from_page,
                        "first_name": first_name,
                        "surname": surname,
                    }
                    return render_template(
                        "add_book.html",
                        authors=authors,
                        form_data=form_data,
                        **context,
                    )

                surname = request.form["surname"]
                author.create_author(first_name, surname)
                created = author.get_author_by_id(db.last_insert_id())
                form_data = {"page": from_page + 1}
                return render_template(
                    "add_book.html",
                    author=created,
                    form_data=form_data,
                    **context,
                )
            else:
                abort(400)

        if from_page == 2:
            form_author = author.get_author_from_form()
            if (
                "book-name-search" not in request.form
                or not request.form["book-name-search"]
            ):
                flash("Anna kirjan nimi", "error")
                form_data = {"page": from_page}
                return render_template(
                    "add_book.html",
                    author=form_author,
                    form_data=form_data,
                    **context,
                )

            books = library.search_books_from_author(
                form_author.id, request.form["book-name-search"]
            )
            form_data = {
                "page": from_page + 1,
                "book_name": request.form["book-name-search"],
            }
            return render_template(
                "add_book.html",
                author=form_author,
                books=books,
                form_data=form_data,
                **context,
            )

        if from_page == 3:
            if "selected-form" not in request.form:
                abort(400)

            selected_form = request.form["selected-form"]
            if selected_form == "select-book":
                form_author = author.get_author_from_form()

                if "book" not in request.form or not request.form["book"]:
                    flash("Sinun tulee valita kirja", "error")
                    books = library.search_books_from_author(
                        form_author.id, request.form["book-name-search"]
                    )
                    form_data = {
                        "page": from_page,
                        "book_name": request.form["book-name-search"],
                    }
                    return render_template(
                        "add_book.html",
                        author=form_author,
                        books=books,
                        form_data=form_data,
                        **context,
                    )

                lib_id = library.get_user_library(
                    cast(int, session["user_id"])
                )
                if not lib_id:
                    abort(400)
                book_id = int(request.form["book"])
                selected = library.get_book_by_id(book_id)
                if not selected:
                    abort(400)
                selected_author = author.get_author_by_id(form_author.id)
                if not selected_author:
                    abort(400)
                library.add_book_to_library(selected.id, selected_author.id)
                return redirect("/kirja/" + str(book_id))
            elif selected_form == "new-book":
                form_author = author.get_author_from_form()
                if (
                    "book-name" not in request.form
                    or not request.form["book-name"]
                ):
                    flash("Anna kirjan nimi", "error")
                    books = library.search_books_from_author(
                        form_author.id, request.form["book-name-search"]
                    )
                    form_data = {
                        "page": from_page,
                        "book_name": request.form["book-name-search"],
                    }
                    return render_template(
                        "add_book.html",
                        author=form_author,
                        books=books,
                        form_data=form_data,
                        **context,
                    )

                if (
                    "class-search" not in request.form
                    or not request.form["class-search"]
                ):
                    flash("Anna hakusanat luokittelulle", "error")
                    books = library.search_books_from_author(
                        form_author.id, request.form["book-name-search"]
                    )
                    form_data = {
                        "page": from_page,
                        "book_name": request.form["book-name-search"],
                    }
                    return render_template(
                        "add_book.html",
                        author=form_author,
                        books=books,
                        form_data=form_data,
                        **context,
                    )
                book_class = library.search_classification(
                    request.form["class-search"]
                )
                form_data = {
                    "page": from_page + 1,
                    "isbn": request.form["isbn"],
                    "book_name": request.form["book-name"],
                    "class_search": request.form["class-search"],
                    "last_class_search": request.form["class-search"],
                }
                return render_template(
                    "add_book.html",
                    author=form_author,
                    library_classes=book_class,
                    form_data=form_data,
                    **context,
                )
            else:
                abort(400)

        if from_page == 4:
            if "selected-form" not in request.form:
                abort(400)

            selected_form = request.form["selected-form"]
            if selected_form == "select":
                form_author = author.get_author_from_form()
                if "class" not in request.form or not request.form["class"]:
                    flash("Sinun tulee valita luokitus", "error")
                    book_class = library.search_classification(
                        request.form["last-class-search"]
                    )
                    form_data = {
                        "page": from_page,
                        "isbn": request.form["isbn"],
                        "book_name": request.form["book-name"],
                        "last_class_search": request.form["last-class-search"],
                    }
                    return render_template(
                        "add_book.html",
                        author=form_author,
                        library_classes=book_class,
                        form_data=form_data,
                        **context,
                    )
                selected_author = author.get_author_by_id(form_author.id)
                if not selected_author:
                    abort(400)
                book_class = library.get_classification_by_id(
                    int(request.form["class"])
                )
                # If the class for the book is not found, the user has
                # probably changed the form, thus the request is bad.
                if not book_class:
                    abort(400)
                library.create_book(
                    isbn=request.form["isbn"],
                    name=request.form["book-name"],
                    author_id=selected_author.id,
                    class_id=book_class.id,
                )
                book_id = db.last_insert_id()
                if not book_id:
                    abort(400)
                lib_id = library.get_user_library(
                    cast(int, session["user_id"])
                )
                if not lib_id:
                    abort(400)
                library.add_book_to_library(book_id, selected_author.id)
                return redirect("/kirja/" + str(book_id))
            elif selected_form == "search":
                form_author = author.get_author_from_form()
                if (
                    "class-search" not in request.form
                    or not request.form["class-search"]
                ):
                    flash("Sinun tulee antaa hakusana", "error")
                    book_class = library.search_classification(
                        request.form["last-class-search"]
                    )
                    form_data = {
                        "page": from_page,
                        "isbn": request.form["isbn"],
                        "book_name": request.form["book-name"],
                        "class_search": request.form["last-class-search"],
                        "last_class_search": request.form["last-class-search"],
                    }
                    return render_template(
                        "add_book.html",
                        author=form_author,
                        library_classes=book_class,
                        form_data=form_data,
                        **context,
                    )
                book_class = library.search_classification(
                    request.form["class-search"]
                )
                form_data = {
                    "page": from_page,
                    "isbn": request.form["isbn"],
                    "book_name": request.form["book-name"],
                    "class_search": request.form["class-search"],
                    "last_class_search": request.form["class-search"],
                }
                return render_template(
                    "add_book.html",
                    author=form_author,
                    library_classes=book_class,
                    form_data=form_data,
                    **context,
                )
            else:
                abort(400)

    # Manually init the form data for the initial GET. The rest of the
    # requests during the book adding process are done through POSTs, so
    # doing a GET resets the form (as it should). If the form data were
    # not cleared when loading the page with GET again, the form might
    # become quite broken.
    form_data = {"page": 0}

    # If the method is not "POST", I can assume it's "GET" (might also
    # be "HEAD" or "OPTIONS", but Flask takes care of those for us).
    return render_template("add_book.html", form_data=form_data, **context)


@app.errorhandler(401)
def handle_unauthorized(_: object):
    return render_template("401.html", **context), 401


@app.errorhandler(404)
def handle_not_found(_: object):
    return render_template("404.html", **context), 404


@app.errorhandler(500)
def handle_internal_server_error(_: object):
    return render_template("500.html", **context), 500
