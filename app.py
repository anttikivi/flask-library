import os
import secrets

from flask import Flask, flash, redirect, render_template, request, session
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

        # TODO: Log in the user.

        # TODO: Redirect to the user page.
        return redirect("/")

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


@app.errorhandler(404)
def handle_not_found(_: object):
    return render_template("404.html", **context), 404


@app.errorhandler(500)
def handle_internal_server_error(_: object):
    return render_template("500.html", **context), 500
