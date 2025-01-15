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

Before starting the server, you need to initalize the database. First create the
database tables.

    sqlite3 database.db < schema.sql

After that, you need to insert the values for classification. The data for the
`classification` and `class_index_words` tables is parsed from the data for the
Finnish Public Libraries Classification System using a utility script at
[scripts/gen_sql_init.py](scripts/gen_sql_init.py). The script generates the SQL
statements for inserting the data and outputs it to stdout.

    ./scripts/gen_sql_init.py | sqlite3 database.db

If running the script fail, this may be due to insufficient permissions. Fix
this by running:

    chmod +x ./scripts/gen_sql_init.py

Running untrusted statements is a bad idea, so you can first redirect the output
to a file for inspecting.

    ./scripts/gen_sql_init.py > init.sql

Running the statements takes a while. It runs 26,625 statements in total.

Start the local server.

    flask run

The application should now be accessible at
[`127.0.0.1:5000`](http://127.0.0.1:5000)!

## Development

This project uses [Ruff](https://docs.astral.sh/ruff/) for linting and
formatting code Python code as it is faster than many of the alternatives. You
can install Ruff either to you local virtual environment or globally using
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

For formatting the Jinja2 template files (files in [`/templates`](templates)),
you can use [Prettier](https://prettier.io). I was also annoyed by the
formatting decisions that the HTML language server I use did with the Jinja2
files thinking that they are HTML, so I let Prettier take over formatting with
its Jinja2 plugin. First install the packages.

    npm install

Then run the formatter.

    npm run format

## License

Copyright (c) 2025 Antti Kivi

This project is licensed under the MIT License. Please see the
[LICENSE](LICENSE) file for more information.

This repository also contains the data for the PLC - Finnish Public Libraries
Classification System. The data is stored at
[scripts/ykl-skos.rdf.xmp](scripts/ykl-skos.rdf.xmp). This data is released into
the public domain under
[CC0 1.0 Universal](https://creativecommons.org/publicdomain/zero/1.0/). Please
visit the [website](https://finto.fi/ykl/fi/) for the PLC for more information.
