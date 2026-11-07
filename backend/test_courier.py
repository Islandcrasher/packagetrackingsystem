"""Backend tests for features #7 and #8.   Run:  python -m unittest test_courier -v"""
import tempfile
import unittest
from pathlib import Path

import db as dbmod
from werkzeug.security import generate_password_hash


class CourierApiTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        dbmod.DB_PATH = Path(self.tmp.name) / "test.db"
        dbmod.init_db()

        from app import create_app

        self.app = create_app()
        con = dbmod.sqlite3.connect(dbmod.DB_PATH)
        pw = generate_password_hash("Password1")

        def user(name, email, role):
            return con.execute(
                "INSERT INTO users (name,email,phone,password_hash,role) VALUES (?,?,?,?,?)",
                (name, email, "01000000000", pw, role),
            ).lastrowid

        self.customer = user("Cust", "c@x.com", "user")
        self.courier = user("Cour", "k@x.com", "courier")
        self.courier2 = user("Cour2", "k2@x.com", "courier")
        self.admin = user("Adm", "a@x.com", "admin")
        self.order = self._order(con, self.courier)
        self.other_order = self._order(con, self.courier2)
        self.unassigned = self._order(con, None)
        con.commit()
        con.close()
        self.client = self.app.test_client()

    def tearDown(self):
        self.tmp.cleanup()

    def _order(self, con, courier_id):
        return con.execute(
            "INSERT INTO orders (user_id,pickup_location,dropoff_location,package_details,"
            "delivery_time,courier_id) VALUES (?,?,?,?,?,?)",
            (self.customer, "A", "B", "box", "2030-01-01T10:00+00:00", courier_id),
        ).lastrowid

    def login(self, email, client=None):
        client = client or self.client
        r = client.post("/api/auth/login", json={"email": email, "password": "Password1"})
        self.assertEqual(r.status_code, 200)
        return r.get_json()["user"]

    # ---- auth / roles
    def test_login_returns_role(self):
        self.assertEqual(self.login("k@x.com")["role"], "courier")

    def test_requires_login(self):
        r = self.client.get(f"/api/courier/{self.courier}/orders")
        self.assertEqual(r.status_code, 401)

    def test_customer_cannot_use_courier_endpoints(self):
        self.login("c@x.com")
        self.assertEqual(self.client.get(f"/api/courier/{self.courier}/orders").status_code, 403)
        self.assertEqual(self.client.post(f"/api/courier/orders/{self.order}/accept").status_code, 403)
        r = self.client.patch(f"/api/courier/orders/{self.order}/status", json={"status": "picked_up"})
        self.assertEqual(r.status_code, 403)

    # ---- feature 7
    def test_list_only_assigned_orders(self):
        self.login("k@x.com")
        r = self.client.get(f"/api/courier/{self.courier}/orders")
        self.assertEqual(r.status_code, 200)
        ids = [o["id"] for o in r.get_json()["orders"]]
        self.assertEqual(ids, [self.order])
        self.assertEqual(r.get_json()["orders"][0]["customer_name"], "Cust")

    def test_cannot_list_other_couriers_orders(self):
        self.login("k@x.com")
        self.assertEqual(self.client.get(f"/api/courier/{self.courier2}/orders").status_code, 403)

    def test_admin_can_list_any_courier(self):
        self.login("a@x.com")
        r = self.client.get(f"/api/courier/{self.courier2}/orders")
        self.assertEqual(r.status_code, 200)

    def test_unknown_courier_404(self):
        self.login("a@x.com")
        self.assertEqual(self.client.get("/api/courier/9999/orders").status_code, 404)
        self.assertEqual(self.client.get(f"/api/courier/{self.customer}/orders").status_code, 404)

    def test_accept_order(self):
        self.login("k@x.com")
        r = self.client.post(f"/api/courier/orders/{self.order}/accept")
        self.assertEqual(r.status_code, 200)
        o = r.get_json()["order"]
        self.assertEqual(o["status"], "accepted")
        self.assertEqual(o["courier_name"], "Cour")  # customer sees courier info
        self.assertEqual(self.client.post(f"/api/courier/orders/{self.order}/accept").status_code, 409)

    def test_decline_order(self):
        self.login("k@x.com")
        r = self.client.post(f"/api/courier/orders/{self.order}/decline")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(self.client.get(f"/api/courier/{self.courier}/orders").get_json()["orders"], [])
        con = dbmod.sqlite3.connect(dbmod.DB_PATH)
        row = con.execute("SELECT status, courier_id FROM orders WHERE id=?", (self.order,)).fetchone()
        self.assertEqual(row, ("pending", None))
        hist = con.execute("SELECT status FROM order_status_history WHERE order_id=?", (self.order,)).fetchall()
        self.assertEqual(hist, [("declined",)])

    def test_cannot_decline_after_accept(self):
        self.login("k@x.com")
        self.client.post(f"/api/courier/orders/{self.order}/accept")
        self.assertEqual(self.client.post(f"/api/courier/orders/{self.order}/decline").status_code, 409)

    def test_cannot_touch_other_couriers_or_unassigned_order(self):
        self.login("k@x.com")
        for oid in (self.other_order, self.unassigned, 9999):
            self.assertEqual(self.client.post(f"/api/courier/orders/{oid}/accept").status_code, 404)
            self.assertEqual(self.client.get(f"/api/courier/orders/{oid}").status_code, 404)
            r = self.client.patch(f"/api/courier/orders/{oid}/status", json={"status": "picked_up"})
            self.assertEqual(r.status_code, 404)

    # ---- feature 8
    def test_full_status_flow_and_history(self):
        self.login("k@x.com")
        url = f"/api/courier/orders/{self.order}/status"
        self.client.post(f"/api/courier/orders/{self.order}/accept")
        for status in ("picked_up", "in_transit", "delivered"):
            r = self.client.patch(url, json={"status": status})
            self.assertEqual(r.status_code, 200, r.get_json())
            self.assertEqual(r.get_json()["order"]["status"], status)
        history = [h["status"] for h in self.client.get(f"/api/courier/orders/{self.order}").get_json()["history"]]
        self.assertEqual(history, ["accepted", "picked_up", "in_transit", "delivered"])

    def test_status_must_follow_order(self):
        self.login("k@x.com")
        url = f"/api/courier/orders/{self.order}/status"
        self.assertEqual(self.client.patch(url, json={"status": "picked_up"}).status_code, 409)  # not accepted yet
        self.client.post(f"/api/courier/orders/{self.order}/accept")
        self.assertEqual(self.client.patch(url, json={"status": "delivered"}).status_code, 409)  # skipping
        self.assertEqual(self.client.patch(url, json={"status": "picked_up"}).status_code, 200)
        self.assertEqual(self.client.patch(url, json={"status": "picked_up"}).status_code, 409)  # repeat

    def test_invalid_status_values(self):
        self.login("k@x.com")
        url = f"/api/courier/orders/{self.order}/status"
        self.client.post(f"/api/courier/orders/{self.order}/accept")
        for body in ({}, {"status": ""}, {"status": "flying"}, {"status": "accepted"}, {"status": 5}, {"status": None}):
            self.assertEqual(self.client.patch(url, json=body).status_code, 400, body)
        r = self.client.patch(url, data="not json", content_type="application/json")
        self.assertEqual(r.status_code, 400)

    def test_cancelled_order_cannot_be_updated(self):
        con = dbmod.sqlite3.connect(dbmod.DB_PATH)
        con.execute("UPDATE orders SET status='cancelled' WHERE id=?", (self.order,))
        con.commit()
        con.close()
        self.login("k@x.com")
        self.assertEqual(self.client.post(f"/api/courier/orders/{self.order}/accept").status_code, 409)
        r = self.client.patch(f"/api/courier/orders/{self.order}/status", json={"status": "picked_up"})
        self.assertEqual(r.status_code, 409)

    def test_delivered_is_final(self):
        self.login("k@x.com")
        url = f"/api/courier/orders/{self.order}/status"
        self.client.post(f"/api/courier/orders/{self.order}/accept")
        for s in ("picked_up", "in_transit", "delivered"):
            self.client.patch(url, json={"status": s})
        self.assertEqual(self.client.patch(url, json={"status": "delivered"}).status_code, 409)

    def test_customer_sees_status_and_courier(self):
        self.login("k@x.com")
        self.client.post(f"/api/courier/orders/{self.order}/accept")
        self.client.patch(f"/api/courier/orders/{self.order}/status", json={"status": "picked_up"})
        cust = self.app.test_client()
        self.login("c@x.com", cust)
        o = cust.get(f"/api/orders/{self.order}").get_json()["order"]
        self.assertEqual((o["status"], o["courier_name"]), ("picked_up", "Cour"))


class MigrationTest(unittest.TestCase):
    def test_old_database_gets_new_columns(self):
        with tempfile.TemporaryDirectory() as tmp:
            dbmod.DB_PATH = Path(tmp) / "old.db"
            con = dbmod.sqlite3.connect(dbmod.DB_PATH)
            con.executescript(
                "CREATE TABLE users (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, "
                "email TEXT NOT NULL UNIQUE, phone TEXT NOT NULL, password_hash TEXT NOT NULL, "
                "created_at TEXT NOT NULL DEFAULT (datetime('now')));"
                "CREATE TABLE orders (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, "
                "pickup_location TEXT NOT NULL, dropoff_location TEXT NOT NULL, package_details TEXT NOT NULL, "
                "delivery_time TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'pending', courier_name TEXT, "
                "courier_phone TEXT, created_at TEXT NOT NULL DEFAULT (datetime('now')));"
                "INSERT INTO users (name,email,phone,password_hash) VALUES ('a','a@a.com','1','x');"
            )
            con.commit()
            con.close()
            dbmod.init_db()
            dbmod.init_db()  # running twice must be safe
            con = dbmod.sqlite3.connect(dbmod.DB_PATH)
            self.assertIn("role", dbmod._columns(con, "users"))
            self.assertIn("courier_id", dbmod._columns(con, "orders"))
            self.assertEqual(con.execute("SELECT role FROM users").fetchone()[0], "user")
            con.close()


if __name__ == "__main__":
    unittest.main()
