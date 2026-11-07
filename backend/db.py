import sqlite3
from pathlib import Path

from flask import g

DB_PATH = Path(__file__).resolve().parent / "app.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT NOT NULL,
    email         TEXT NOT NULL UNIQUE,
    phone         TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    role          TEXT NOT NULL DEFAULT 'user',
    created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS orders (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id           INTEGER NOT NULL,
    pickup_location   TEXT NOT NULL,
    dropoff_location  TEXT NOT NULL,
    package_details   TEXT NOT NULL,
    delivery_time     TEXT NOT NULL,
    status            TEXT NOT NULL DEFAULT 'pending',
    courier_name      TEXT,
    courier_phone     TEXT,
    courier_id        INTEGER,
    created_at        TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
    FOREIGN KEY (courier_id) REFERENCES users (id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_orders_user_id ON orders (user_id);

-- Feature #8: every status change is recorded here.
CREATE TABLE IF NOT EXISTS order_status_history (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id    INTEGER NOT NULL,
    status      TEXT NOT NULL,
    changed_by  INTEGER,
    changed_at  TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (order_id) REFERENCES orders (id) ON DELETE CASCADE,
    FOREIGN KEY (changed_by) REFERENCES users (id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_history_order_id ON order_status_history (order_id);
"""

# Columns added after the first version of the schema. init_db() adds them to
# an already-existing app.db so nobody has to delete their database.
MIGRATIONS = [
    ("users", "role", "TEXT NOT NULL DEFAULT 'user'"),
    ("orders", "courier_id", "INTEGER REFERENCES users (id) ON DELETE SET NULL"),
]

POST_MIGRATION = """
CREATE INDEX IF NOT EXISTS idx_orders_courier_id ON orders (courier_id);
"""


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        connection = sqlite3.connect(DB_PATH)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        g.db = connection
    return g.db


def close_db(_exception=None) -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()


def _columns(connection: sqlite3.Connection, table: str) -> set:
    return {row[1] for row in connection.execute(f"PRAGMA table_info({table})")}


def init_db() -> None:
    connection = sqlite3.connect(DB_PATH)
    try:
        connection.executescript(SCHEMA)
        for table, column, ddl in MIGRATIONS:
            if column not in _columns(connection, table):
                connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")
        connection.executescript(POST_MIGRATION)
        connection.commit()
    finally:
        connection.close()
