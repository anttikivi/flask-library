from flask import abort, request, session


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
