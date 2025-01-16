import os
import secrets

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

import env
import users

env.read_env_file()

app = Flask(__name__)
app.secret_key = os.environ["SECRET_KEY"]

context = {"site": {"subtitle": "Kirjat purkissa", "title": "Flask-kirjasto"}}


@app.route("/", methods=["GET"])
def index() -> str:
    return render_template("index.html", **context, is_home=True)


@app.route("/kayttaja/<string:username>", methods=["GET"])
def user_page(username: str):
    user = users.get_users_by_name(username)
    if not user:
        abort(404)
    return render_template("user.html", user=user, **context)


@app.route("/asetukset/", methods=["GET", "POST"])
def edit_user():
    username: str = session["username"]
    user = users.get_users_by_name(username)

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

    if "username" not in session:
        abort(401)
    if not user:
        # The session has a username so we can expect to find the user
        # in the database.
        abort(500)
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


@app.errorhandler(401)
def handle_unauthorized(_: object):
    return render_template("401.html", **context), 401


@app.errorhandler(404)
def handle_not_found(_: object):
    return render_template("404.html", **context), 404


@app.errorhandler(500)
def handle_internal_server_error(_: object):
    return render_template("500.html", **context), 500
