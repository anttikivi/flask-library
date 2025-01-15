from flask import Flask, render_template
import os

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
