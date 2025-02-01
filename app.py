import math
import os
import secrets
from collections.abc import Sequence
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


def check_csrf_from_param():
    token = request.args.get("token")
    if not token:
        abort(403)
    if token != session["csrf_token"]:
        abort(403)


def check_login():
    if "user_id" not in session:
        abort(401)


@app.route("/", methods=["GET"])
def index() -> str:
    books = library.get_popular_books(10)
    owned: Sequence[library.BookIDCounts] = []
    if "user_id" in session:
        owned = library.get_owned_book_counts_by_id(
            cast(int, session["user_id"])
        )
    return render_template(
        "index.html", books=books, owned=owned, is_home=True, **context
    )


########################################################################
# USER MANAGEMENT
########################################################################


@app.route("/kayttaja/<string:username>/", methods=["GET"])
def user_page(username: str):
    user = users.get_users_by_name(username)
    if not user:
        abort(404)
    return render_template("user.html", user=user, **context)


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
        check_csrf()

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

    page_count = math.ceil(book_count / page_size)

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
    if "user_id" in session:
        owned = library.get_owned_book_counts_by_id(
            cast(int, session["user_id"])
        )

    return render_template(
        "library.html",
        books=books,
        page=page,
        page_count=page_count,
        page_size=page_size,
        add_per_page_param=add_per_page_param,
        owned=owned,
        **context,
    )


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
        check_login()

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
                library.add_book_to_user(
                    selected.id, cast(int, session["user_id"])
                )
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
                library.add_book_to_user(
                    book_id, cast(int, session["user_id"])
                )
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
    return render_template(
        "book.html",
        author=book_author,
        book=book,
        book_class=book_class,
        owns=owns,
        **context,
    )


@app.route("/kirja/<int:book_id>/muokkaa/", methods=["GET", "POST"])
def edit_book(book_id: int):
    check_login()

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
        check_csrf()

        if "what" not in request.form:
            abort(400)
        what = request.form["what"]
        if what != "name" and what != "author" and what != "author-update":
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
            print("Rendering the search results ")
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


@app.route("/add-one-book/", methods=["GET"])
def add_one_book():
    check_csrf_from_param()
    check_login()

    book_id = request.args.get("id")
    user_id = cast(int, session["user_id"])
    if not book_id or not user_id:
        abort(400)

    library.add_book_to_user(int(book_id), user_id)

    return redirect(request.referrer)


@app.route("/delete-one-book/", methods=["GET"])
def delete_one_book():
    check_csrf_from_param()
    check_login()

    book_id = request.args.get("id")
    user_id = cast(int, session["user_id"])
    if not book_id or not user_id:
        abort(400)

    library.remove_books_from_user(int(book_id), user_id, 1)

    return redirect(request.referrer)


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
