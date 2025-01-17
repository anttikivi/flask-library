CREATE TABLE users (
  id INTEGER PRIMARY KEY,
  username TEXT NOT NULL UNIQUE,
  password_hash TEXT NOT NULL
);

-- The table classification uses nested set model for representing the tree in
-- the database. This is choice is done for two reasons:
-- 1. This model can be efficient when the tree is quite deep and read ofter.
--    While there is not *really* that many classes in the classification, but
--    for the purposes of this program the dataset is large.
-- 2. For this library, this table does not change after it has been created at
--    initialization. The app does not allow users to add their own categories
--    as a feature - it is a choice that the books are organized according to a
--    pre-set classification.
CREATE TABLE classification (
  id INTEGER PRIMARY KEY,
  key TEXT NOT NULL UNIQUE,
  label TEXT,
  lft INTEGER NOT NULL,
  rgt INTEGER NOT NULL
);

-- The table class_index_words maps the index words for a class to the class.
-- NOTE: The `label` is duplicated into this table by design: it is in
-- classification as it is used as the title of the class, but here it is used
-- for searching.
CREATE TABLE class_index_words (
  id INTEGER PRIMARY KEY,
  class_id INTEGER NOT NULL,
  word TEXT NOT NULL,
  FOREIGN KEY(class_id) REFERENCES classification(id)
);

CREATE TABLE authors (
  id INTEGER PRIMARY KEY,
  first_name TEXT,
  surname TEXT NOT NULL -- Authors are sorted, as names usually, by surname. This also works as a pen name if an author only has a one-part name.
);

CREATE TABLE books (
  id INTEGER PRIMARY KEY,
  isbn TEXT,
  name TEXT,
  author_id INTEGER NOT NULL,
  class_id INTEGER NOT NULL,
  FOREIGN KEY(author_id) REFERENCES authors(id),
  FOREIGN KEY(class_id) REFERENCES classification(id)
);

CREATE TABLE libraries (
  id INTEGER PRIMARY KEY,
  user_id INTEGER NOT NULL,
  FOREIGN KEY(user_id) REFERENCES users(id)
);

CREATE TABLE book_ownerships (
  id INTEGER PRIMARY KEY,
  book_id INTEGER NOT NULL,
  library_id INTEGER NOT NULL,
  FOREIGN KEY(book_id) REFERENCES books(id),
  FOREIGN KEY(library_id) REFERENCES libraries(id)
);
