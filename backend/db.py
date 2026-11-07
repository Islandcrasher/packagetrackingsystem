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
    created_at        TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_orders_user_id ON orders (user_id);
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


def init_db() -> None:
    connection = sqlite3.connect(DB_PATH)
    try:
        connection.executescript(SCHEMA)
        connection.commit()
    finally:
        connection.close()
