import os
from flask import Flask, flash, redirect, render_template, request
from werkzeug.wrappers import Response

import env

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
    # TODO: Redirect to the user page.
    return redirect("/")
