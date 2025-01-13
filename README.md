# flask-library

`flask-library` is a small web application for keeping a personal library
database.

## Planned features

While this project uses English for development, the user-facing web application
will be implemented in Finnish and using the Finnish Public Libraries
Classification System if possible during the course. The system is available in
XML, but parsing it into the application might not be worth it within the scope
of this application.

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

## License

Copyright (c) 2025 Antti Kivi

This project is licensed under the MIT license. Please see the
[LICENSE](LICENSE) file for more information.
