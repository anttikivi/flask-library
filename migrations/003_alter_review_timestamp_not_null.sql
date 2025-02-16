BEGIN TRANSACTION;

UPDATE reviews SET time = datetime('now') WHERE time IS NULL;

CREATE TABLE IF NOT EXISTS new_reviews (
  id INTEGER PRIMARY KEY,
  user_id INTEGER NOT NULL,
  book_id INTEGER NOT NULL,
  stars INTEGER NOT NULL,
  message TEXT,
  time TEXT NOT NULL,
  last_edited TEXT NOT NULL,
  FOREIGN KEY(user_id) REFERENCES users(id),
  FOREIGN KEY(book_id) REFERENCES books(id)
);

INSERT INTO new_reviews (
  id,
  user_id,
  book_id,
  stars,
  message,
  time,
  last_edited
)
SELECT
  id,
  user_id,
  book_id,
  stars,
  message,
  time,
  time
FROM reviews;

DROP TABLE reviews;

ALTER TABLE new_reviews RENAME TO reviews;

COMMIT;
