"""Demo data for the courier features.

Run from the backend folder:

    python seed_demo.py
        Creates a courier account, a demo customer and 3 demo orders that are
        already assigned to the courier.

    python seed_demo.py assign ORDER_ID courier@swiftship.com
        Assigns any existing order to a courier (this is what the admin's
        "Assign Orders to Courier" feature does from the UI).

    python seed_demo.py make-courier someone@example.com
        Turns an already registered user into a courier.
"""
import sys
from datetime import datetime, timedelta, timezone

from werkzeug.security import generate_password_hash

from db import DB_PATH, init_db
import sqlite3

COURIER = ("Karim Courier", "courier@swiftship.com", "+201000000001", "Courier@123")
CUSTOMER = ("Demo Customer", "customer@swiftship.com", "+201000000002", "Customer@123")


def connect():
    init_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def ensure_user(conn, name, email, phone, password, role):
    row = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
    if row:
        conn.execute("UPDATE users SET role = ? WHERE id = ?", (role, row["id"]))
        return row["id"]
    cur = conn.execute(
        "INSERT INTO users (name, email, phone, password_hash, role) VALUES (?, ?, ?, ?, ?)",
        (name, email, phone, generate_password_hash(password), role),
    )
    return cur.lastrowid


def seed():
    conn = connect()
    courier_id = ensure_user(conn, *COURIER, "courier")
    customer_id = ensure_user(conn, *CUSTOMER, "user")

    has_orders = conn.execute(
        "SELECT 1 FROM orders WHERE user_id = ? AND courier_id = ?",
        (customer_id, courier_id),
    ).fetchone()
    if not has_orders:
        base = datetime.now(timezone.utc) + timedelta(days=1)
        demo = [
            ("Nasr City, Cairo", "Maadi, Cairo", "Small box - phone case", 0),
            ("Heliopolis, Cairo", "Zamalek, Cairo", "Documents envelope", 2),
            ("6th of October City", "Dokki, Giza", "Shoes - size 42", 4),
        ]
        for pickup, dropoff, details, hours in demo:
            when = (base + timedelta(hours=hours)).isoformat(timespec="minutes")
            conn.execute(
                "INSERT INTO orders (user_id, pickup_location, dropoff_location, "
                "package_details, delivery_time, courier_id) VALUES (?, ?, ?, ?, ?, ?)",
                (customer_id, pickup, dropoff, details, when, courier_id),
            )
    conn.commit()
    conn.close()
    print("Done.")
    print(f"  Courier : {COURIER[1]} / {COURIER[3]}")
    print(f"  Customer: {CUSTOMER[1]} / {CUSTOMER[3]}")


def assign(order_id, email):
    conn = connect()
    courier = conn.execute(
        "SELECT id FROM users WHERE email = ? AND role = 'courier'", (email.lower(),)
    ).fetchone()
    if not courier:
        sys.exit(f"No courier with email {email}")
    cur = conn.execute(
        "UPDATE orders SET courier_id = ?, courier_name = NULL, courier_phone = NULL, "
        "status = 'pending' WHERE id = ?",
        (courier["id"], order_id),
    )
    conn.commit()
    if cur.rowcount == 0:
        sys.exit(f"No order with id {order_id}")
    print(f"Order {order_id} assigned to {email}")


def make_courier(email):
    conn = connect()
    cur = conn.execute("UPDATE users SET role = 'courier' WHERE email = ?", (email.lower(),))
    conn.commit()
    if cur.rowcount == 0:
        sys.exit(f"No user with email {email}")
    print(f"{email} is now a courier")


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        seed()
    elif args[0] == "assign" and len(args) == 3:
        assign(int(args[1]), args[2])
    elif args[0] == "make-courier" and len(args) == 2:
        make_courier(args[1])
    else:
        print(__doc__)
