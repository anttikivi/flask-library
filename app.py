import os

from flask import Flask, flash, redirect, render_template, request
from werkzeug.wrappers import Response

import env
import users

env.read_env_file()

app = Flask(__name__)
app.secret_key = os.environ["SECRET_KEY"]

context = {"site": {"subtitle": "Kirjat purkissa", "title": "Flask-kirjasto"}}


@app.route("/")
def index() -> str:
    return render_template("index.html", **context, is_home=True)


@app.route("/luo-tili/", methods=["GET", "POST"])
def register() -> str | Response:
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        password_again = request.form["password_again"]
        form_data = {"username": username}

        if password != password_again:
            flash("Salasanat eivät täsmää", "error")
            return render_template(
                "register.html", form_data=form_data, **context
            )

        if users.get_users_by_name(username):
            flash("Käyttäjänimi on jo varattu", "error")
            return render_template(
                "register.html", form_data=form_data, **context
            )

        # Because I check the username's uniqueness above, there is no
        # need to check for error here: if the database operation fails,
        # it is desirable to return an internal server error as that
        # tells me that there is really a bug in the program. I try to
        # stay away from using excetion for flow control.
        users.create_user(username, password)

        # TODO: Redirect to the user page.
        return redirect("/")

    # If the method is not "POST", I can assume it's "GET" (might also
    # be "HEAD" or "OPTIONS", but Flask takes care of those for us).
    return render_template("register.html", **context)
