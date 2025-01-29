# flask-library

`flask-library` is a small web application for keeping a personal library
database.

## Features

While this project uses English for development, the user-facing web application
will be implemented in Finnish and using the
[Finnish Public Libraries Classification System](https://finto.fi/ykl/fi/).

### Planned Features

As of right now, here is the list of the planned features. As the development
progresses, I’ll mark the checkboxes as the features in question get
implemented. The features that will be implemented might change during
development.

- [x] The user can create an account and log in.
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

> The app depends only on Flask. If you want to, running `pip install flask`
> should also do the job.

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

The last thing the do before running the server is generating the secret key for
Flask. The server reads the secret key reads variables into environment
variables (`os.environ`) from `.env`, and then reads the secret key from
environment variables. You can generate a `.env` file with the key using the
provided script.

    ./scripts/gen_secret_key.py

<!-- prettier-ignore -->
> [!CAUTION]
> The script replaces the `.env` file. Do not run the script if you want to
> preserve what is in the file.

Once again, make sure the script has sufficient permissions.

    chmod +x ./scripts/gen_secret_key.py

Now you can start the local server.

    flask run

The application should now be accessible at
[`127.0.0.1:5000`](http://127.0.0.1:5000)!

## Development

### Design Decisions

One of the noteworthy design decisions within the scope of the course that this
app’s been written for is that even though the code is in English, as one would
expect, the user facing interface is in Finnish. This includes the URLs that the
user might be expected to type. For example, if you were to browse a Finnish
website and you wanted to create a user there, it would be confusing if you
suddenly had to type the URL for registration in English, i.e. `/register`
instead of `/rekisteroidy` or `/luo-tili`. That’s why you’ll see a combination
of Finnish and English routes within the app. This can also be helpful—this
let’s you quickly distinguish between the actual pages of the app and the API
endpoints.

### Tools

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
