from flask import Flask, render_template

app = Flask(__name__)

context = {"site": {"subtitle": "Kirjat purkissa", "title": "Flask-kirjasto"}}


@app.route("/")
def index() -> str:
    return render_template("index.html", **context, is_home=True)
