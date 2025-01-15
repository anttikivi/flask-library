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
  class_id INTEGER REFERENCES classification,
  word TEXT NOT NULL
);
