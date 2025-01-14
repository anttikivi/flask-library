# flask-library

`flask-library` is a small web application for keeping a personal library
database.

## Features

While this project uses English for development, the user-facing web application
will be implemented in Finnish and using the
[Finnish Public Libraries Classification System](https://finto.fi/ykl/fi/) if
possible during the course. The system is available in XML, but parsing it into
the application might not be worth it within the scope of this application.

As of right now, here is the list of the planned features. As the development
progresses, I’ll mark the checkboxes as the features in question get
implemented.

- [ ] The user can create an account and log in.
- [ ] Only some information of the user libraries are shown without logging. As
      the app stores information on personal belongings, it is sensible to
      authenticate those who can browse the information in the database.
- [ ] The user can create a “guest” account to browse other users’ libraries
      more freely.
- [ ] When logged in, the user can create, modify, and delete book entries in
      the library. The entries can have all the information you would expect to
      see, like the title, author, genre, ISBN, and freeform thoughts of the
      user on the book.
- [ ] When logged in, the user can provide an image of the books cover.
- [ ] The user can search for books by title, genre, author, ISBN, and
      (possibly) by other factors.
- [ ] The user can view book stats of other users.
- [ ] When logged in, the user can marks books as read.
- [ ] When logged in, the user can comment on other people’s libraries.

## Getting Started

This project uses Python and
[Flask](https://flask.palletsprojects.com/en/stable/) as the main framework.
Please make sure you have at least Python 3.9 installed.

Start by creating a new Python virtual environment.

    python -m venv venv && source ./venv/bin/activate

Install dependencies.

    pip install -r requirements.txt

Start the local server.

    flask run

The application should now be accessible at
[`127.0.0.1:5000`](http://127.0.0.1:5000)!

## Development

This project uses [Ruff](https://docs.astral.sh/ruff/) for linting and
formatting code as it is faster than many of the alternatives. You can install
Ruff either to you local virtual environment or globally using
[pipx](https://github.com/pypa/pipx). To install it in your virtual environment,
make sure you have first enabled it (by running `source ./venv/bin/activate`).

    pip install ruff

To install it globally using pipx, you need to, of course, have pipx installed.
Then you can run:

    pipx install ruff

Please consult the
[Ruff documentation](https://docs.astral.sh/ruff/installation/) for other
installation methods.

The linter and formatter settings for this project are defined in
[`pyproject.toml`](pyproject.toml) as you would expect. Thus, to lint the code,
you can run:

    ruff check

To format the code:

    ruff format

## License

Copyright (c) 2025 Antti Kivi

This project is licensed under the MIT License. Please see the
[LICENSE](LICENSE) file for more information.
