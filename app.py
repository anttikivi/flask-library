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


@app.route("/luo-tili/")
def register() -> str:
    return render_template("register.html", **context)


@app.route("/create-user", methods=["POST"])
def create_user() -> Response:
    username = request.form["username"]
    password = request.form["password"]
    password_again = request.form["password_again"]

    if password != password_again:
        flash("Salasanat eivät täsmää", "error")
        return redirect("/luo-tili/")

    if users.get_users_by_name(username):
        flash("Käyttäjänimi on jo varattu", "error")
        return redirect("/luo-tili/")

    # Because I check the username's uniqueness above, there is no need
    # to check for error here: if the database operation fails, it is
    # desirable to return an internal server error as that tells me that
    # there is really a bug in the program. I try to stay away from
    # using excetion for flow control.
    users.create_user(username, password)

    # TODO: Redirect to the user page.
    return redirect("/")
