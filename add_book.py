from collections.abc import Sequence
from typing import cast

from flask import abort, flash, redirect, render_template, request, session
from werkzeug.wrappers import Response

import author
import checks
import db
import library


def render_page(**context: dict[str, str]) -> str | Response:
    """
    Renders the "add book" page according to the current global request.
    """
    # Regardless of method, unauthenticated users cannot access this
    # page.
    if "user_id" not in session:
        abort(401)

    if request.method == "POST":
        checks.check_csrf()
        checks.check_login()

        # Start by checking that the POST request contains data on from
        # which form page the request was made from. This is done
        # because different attributes of the book are set on different
        # "pages" and the old state is stored in hidden form fields.
        if not request.form or "from-page" not in request.form:
            abort(400)
        from_page = int(request.form["from-page"])

        # First page is the author search.
        if from_page == 0:
            return __render_author_select(
                "first-name-search",
                "surname-search",
                from_page,
                True,
                **context,
            )

        # Second page is the selection or creation of the author. Here
        # we handle either the selection or the creation of the author.
        if from_page == 1:
            if "selected-form" not in request.form:
                abort(400)

            # The request must contain information on which form was
            # selected. The user can either select an author from the
            # search results or create a new one.
            selected_form = request.form["selected-form"]
            if (
                selected_form != "select-author"
                and selected_form != "new-author"
            ):
                abort(400)

            if selected_form == "select-author":
                if "author" not in request.form or not request.form["author"]:
                    flash(
                        "Sinun tulee valita kirjoittaja tai luoda uusi",
                        "error",
                    )
                    # If the author selection form was used but author
                    # was not selected, re-render the page with the
                    # flash.
                    #
                    # If the user has, for some reason, went ahead and
                    # deleted the last surname value from the hidden
                    # field, the form also notes about the missing
                    # surname.
                    return __render_author_select(
                        "last-first-name",
                        "last-surname",
                        from_page,
                        False,
                        **context,
                    )
                author_id = int(request.form["author"])
                selected = author.get_author_by_id(author_id)
                form_data = {"page": from_page + 1}
                return render_template(
                    "add_book.html",
                    author=selected,
                    form_data=form_data,
                    **context,
                )

            if selected_form == "new-author":
                first_name = request.form["first-name"]
                if (
                    "surname" not in request.form
                    or not request.form["surname"]
                ):
                    # If the form is called without the surname that is
                    # required, re-render the page. The flash about the
                    # missing name is added by __render_author_select.
                    # This does the check for the surname field twice,
                    # but that shouldn't be the overhead we are worried
                    # about as, after all, we are using Python.
                    return __render_author_select(
                        "first-name", "surname", from_page, False, **context
                    )
                surname = request.form["surname"]
                author.create_author(first_name, surname)
                created = author.get_author_by_id(db.last_insert_id())
                form_data = {"page": from_page + 1}
                return render_template(
                    "add_book.html",
                    author=created,
                    form_data=form_data,
                    **context,
                )

        # Third page is the book search. Here we only see if the name of
        # the book that the user has given matches any book by the same
        # author already in the database.
        if from_page == 2:
            return __render_book_select(
                "book-name-search",
                author.get_author_from_form(),
                from_page,
                True,
                **context,
            )

        # The fourth page is the classification search. At this point,
        # all of the other values we want to have are in the form fields
        # and the classification is the only thing left. The fifth page
        # is used for creating the new book with the correct
        # classification.
        #
        # This page might also be used for selecting a book from the
        # list of the matches from last step. If that is the case, we
        # just add one copy to the user's library and skip the
        # classification.
        if from_page == 3:
            if "selected-form" not in request.form:
                abort(400)

            selected_form = request.form["selected-form"]

            # The request must contain information on which form was
            # selected. The user can either select a book from the
            # search results or create a new one.
            selected_form = request.form["selected-form"]
            if selected_form != "select-book" and selected_form != "new-book":
                abort(400)

            if selected_form == "select-book":
                form_author = author.get_author_from_form()

                if "book" not in request.form or not request.form["book"]:
                    # If no book is selected, re-render the template and
                    # display flash to guide the user to select a value.
                    return __render_book_select(
                        "book-name-search",
                        form_author,
                        from_page,
                        False,
                        **context,
                    )

                # Fetch the user's library and check if it exists.
                lib_id = library.get_user_library(
                    cast(int, session["user_id"])
                )
                if not lib_id:
                    abort(400)

                # Fetch the book again to ensure that the user has not
                # messed up the values from the form manually.
                book_id = int(request.form["book"])
                selected = library.get_book_by_id(book_id)
                if not selected:
                    abort(400)
                # Fetch the author again to ensure that the user has not
                # messed up the values from the form manually.
                selected_author = author.get_author_by_id(form_author.id)
                if not selected_author:
                    abort(400)

                # If everything is in order, add the book.
                library.add_book_to_user(
                    selected.id, cast(int, session["user_id"])
                )

                # If book was successfully selected and a copy was added
                # to the user's library, redirect to the book's page.
                return redirect("/kirja/" + str(book_id))

            if selected_form == "new-book":
                form_author = author.get_author_from_form()
                if (
                    "book-name" not in request.form
                    or not request.form["book-name"]
                ):
                    flash("Anna kirjan nimi", "error")

                    # If no book name is given, re-render the template
                    # and display flash to guide the user to give a
                    # value.
                    return __render_book_select(
                        "book-name-search",
                        form_author,
                        from_page,
                        False,
                        **context,
                    )

                if (
                    "class-search" not in request.form
                    or not request.form["class-search"]
                ):
                    flash("Anna hakusanat luokittelulle", "error")

                    # If no classification name is given, re-render the
                    # template and display flash to guide the user to
                    # give a value.
                    return __render_book_select(
                        "book-name-search",
                        form_author,
                        from_page,
                        False,
                        **context,
                    )

                return __render_classification_select(
                    isbn_field="isbn",
                    book_name_field="book-name",
                    class_search_field="class-search",
                    add_class_search=True,
                    author=form_author,
                    page=from_page,
                    increment_on_success=True,
                    **context,
                )

        # The fifth page is the classfication selection and the creation
        # of the new book. It can also be a new classification search if
        # the last search was unsuccessful.
        if from_page == 4:
            if "selected-form" not in request.form:
                abort(400)

            selected_form = request.form["selected-form"]
            if selected_form != "select" and selected_form != "search":
                abort(400)

            if selected_form == "select":
                form_author = author.get_author_from_form()
                if "class" not in request.form or not request.form["class"]:
                    flash("Sinun tulee valita luokitus", "error")
                    return __render_classification_select(
                        isbn_field="isbn",
                        book_name_field="book-name",
                        class_search_field="last-class-search",
                        add_class_search=False,
                        author=form_author,
                        page=from_page,
                        increment_on_success=False,
                        **context,
                    )

                # Revalidate the author if the user has manually changed
                # the form.
                selected_author = author.get_author_by_id(form_author.id)
                if not selected_author:
                    abort(400)

                book_class = library.get_classification_by_id(
                    int(request.form["class"])
                )
                # If the class for the book is not found, the user has
                # probably changed the form, thus the request is bad.
                if not book_class:
                    abort(400)
                library.create_book(
                    isbn=request.form["isbn"],
                    name=request.form["book-name"],
                    author_id=selected_author.id,
                    class_id=book_class.id,
                )
                book_id = db.last_insert_id()
                if not book_id:
                    abort(400)
                lib_id = library.get_user_library(
                    cast(int, session["user_id"])
                )
                if not lib_id:
                    abort(400)
                library.add_book_to_user(
                    book_id, cast(int, session["user_id"])
                )
                return redirect("/kirja/" + str(book_id))

            # The select form is used if the original search was not
            # successful. Here we simply perform a new search and
            # re-render the template.
            if selected_form == "search":
                form_author = author.get_author_from_form()
                if (
                    "class-search" not in request.form
                    or not request.form["class-search"]
                ):
                    flash("Sinun tulee antaa hakusana", "error")
                    return __render_classification_select(
                        isbn_field="isbn",
                        book_name_field="book-name",
                        class_search_field="last-class-search",
                        add_class_search=True,
                        author=form_author,
                        page=from_page,
                        increment_on_success=False,
                        **context,
                    )

                return __render_classification_select(
                    isbn_field="isbn",
                    book_name_field="book-name",
                    class_search_field="class-search",
                    add_class_search=True,
                    author=form_author,
                    page=from_page,
                    increment_on_success=False,
                    **context,
                )

    # Manually init the form data for the initial GET. The rest of the
    # requests during the book adding process are done through POSTs, so
    # doing a GET resets the form (as it should). If the form data were
    # not cleared when loading the page with GET again, the form might
    # become quite broken.
    form_data = {"page": 0}

    # If the method is not "POST", I can assume it's "GET" (might also
    # be "HEAD" or "OPTIONS", but Flask takes care of those for us).
    return render_template("add_book.html", form_data=form_data, **context)


def __render_author_select(
    first_name_field: str,
    surname_field: str,
    page: int,
    increment_on_success: bool,
    **context: dict[str, str],
) -> str:
    """
    Renders the author selection page for the book adding.

    The parameters passed to the function are not the actual name values
    that the user gave but the names of the form fields to check. The
    function aborts or renders an error if required form fields are
    missing.

    The function checks for matches with the given parameters and
    populates the page according to them. If the page number should be
    incremented on success (i.e. the function does not need to do error
    handling because of missing fields), `increment_on_success` should
    be set to `True`.
    """
    first_name = request.form[first_name_field]
    if surname_field not in request.form or not request.form[surname_field]:
        flash("Anna sukunimi tai nimimerkki", "error")
        form_data = {"page": page, "first_name": first_name}
        return render_template("add_book.html", form_data=form_data, **context)
    surname = request.form[surname_field]
    authors: Sequence[author.Author] = []

    # See if the name of the author is an exact match and only return
    # that to the user.
    author_match = author.get_author(first_name, surname)
    if author_match:
        authors.append(author_match)

    # If the author was not found right away, search for authors
    # with similar names.
    if not authors:
        authors = author.seach_author(first_name, surname)
    form_data = {
        "page": page + 1 if increment_on_success else page,
        "first_name": first_name,
        "surname": surname,
    }
    return render_template(
        "add_book.html", authors=authors, form_data=form_data, **context
    )


def __render_book_select(
    book_name_field: str,
    author: author.Author,
    page: int,
    increment_on_success: bool,
    **context: dict[str, str],
) -> str:
    """
    Renders the book selection page for the book adding.

    The `book_name_field` is not the actual book name but the name of
    the field for the book name. The function aborts if required form
    fields are missing.

    The function checks for matches with the given parameters and
    populates the page according to them. If the page number should be
    incremented on success (i.e. the function does not need to do error
    handling because of missing fields), `increment_on_success` should
    be set to `True`.
    """

    if not author.id:
        abort(400)
    if (
        book_name_field not in request.form
        or not request.form[book_name_field]
    ):
        flash("Anna kirjan nimi", "error")
        form_data = {"page": page}
        return render_template(
            "add_book.html", author=author, form_data=form_data, **context
        )

    books = library.search_books_from_author(
        author.id, request.form[book_name_field]
    )
    form_data = {
        "page": page + 1 if increment_on_success else page,
        "book_name": request.form[book_name_field],
    }
    return render_template(
        "add_book.html",
        author=author,
        books=books,
        form_data=form_data,
        **context,
    )


def __render_classification_select(
    isbn_field: str,
    book_name_field: str,
    class_search_field: str,
    add_class_search: bool,
    author: author.Author,
    page: int,
    increment_on_success: bool,
    **context: dict[str, str],
) -> str:
    """
    Renders the classification selection page for the book adding.

    The parameters passed to the function are not the actual values
    that the user gave but the names of the form fields to check. The
    function aborts if required form fields are missing.

    The output form data can include `class_search` entry in addition to
    the `last_class_search` entry, and that is required for some
    template configurations. Use the `add_class_search` parameter to set
    that. It is populated with the same value as the `last_class_search`
    entry.

    The function checks for matches with the given parameters and
    populates the page according to them. If the page number should be
    incremented on success (i.e. the function does not need to do error
    handling because of missing fields), `increment_on_success` should
    be set to `True`.
    """
    if isbn_field not in request.form:
        abort(400)
    if book_name_field not in request.form:
        abort(400)
    book_class = library.search_classification(
        request.form[class_search_field]
    )
    form_data = {
        "page": page + 1 if increment_on_success else page,
        "isbn": request.form[isbn_field],
        "book_name": request.form[book_name_field],
        "last_class_search": request.form[class_search_field],
    }

    if add_class_search:
        form_data["class_search"] = request.form[class_search_field]

    return render_template(
        "add_book.html",
        author=author,
        library_classes=book_class,
        form_data=form_data,
        **context,
    )
