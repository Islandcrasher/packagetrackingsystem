"""Backend tests for Features #9 and #10. Run: python -m unittest test_admin -v"""
import tempfile
import unittest
from pathlib import Path

import db as dbmod
from werkzeug.security import generate_password_hash


class AdminApiTests(unittest.TestCase):
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

        self.customer = user("Customer", "customer@example.com", "user")
        self.courier = user("Courier One", "courier@example.com", "courier")
        self.courier2 = user("Courier Two", "courier2@example.com", "courier")
        self.admin = user("Admin", "admin@example.com", "admin")
        self.order = self.make_order(con)
        self.assigned = self.make_order(con, self.courier)
        self.completed = self.make_order(con, self.courier, "delivered")
        con.commit()
        con.close()
        self.client = self.app.test_client()

    def make_order(self, con, courier_id=None, status="pending"):
        return con.execute(
            "INSERT INTO orders (user_id,pickup_location,dropoff_location,package_details,delivery_time,courier_id,status) VALUES (?,?,?,?,?,?,?)",
            (self.customer, "Pickup", "Dropoff", "Box", "2030-01-01T10:00+00:00", courier_id, status),
        ).lastrowid

    def tearDown(self):
        self.tmp.cleanup()

    def login(self, email):
        response = self.client.post("/api/auth/login", json={"email": email, "password": "Password1"})
        self.assertEqual(response.status_code, 200)

    def test_admin_endpoints_require_admin_role(self):
        self.assertEqual(self.client.get("/api/admin/orders").status_code, 401)
        self.login("customer@example.com")
        for method, path in (("get", "/api/admin/orders"), ("get", "/api/admin/couriers"),
                             ("patch", f"/api/admin/orders/{self.order}/status"),
                             ("patch", f"/api/admin/orders/{self.order}/courier"),
                             ("delete", f"/api/admin/orders/{self.order}")):
            response = getattr(self.client, method)(path, json={"status": "pending", "courier_id": self.courier})
            self.assertEqual(response.status_code, 403, path)

    def test_admin_lists_all_orders_with_customer_and_courier(self):
        self.login("admin@example.com")
        orders = self.client.get("/api/admin/orders").get_json()["orders"]
        by_id = {order["id"]: order for order in orders}
        self.assertEqual(len(orders), 3)
        self.assertEqual(by_id[self.assigned]["assigned_courier_name"], "Courier One")
        self.assertEqual(by_id[self.order]["customer_name"], "Customer")

    def test_admin_lists_only_couriers(self):
        self.login("admin@example.com")
        couriers = self.client.get("/api/admin/couriers").get_json()["couriers"]
        self.assertEqual({courier["id"] for courier in couriers}, {self.courier, self.courier2})

    def test_admin_updates_status_and_records_history(self):
        self.login("admin@example.com")
        response = self.client.patch(f"/api/admin/orders/{self.order}/status", json={"status": "in_transit"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["order"]["status"], "in_transit")
        con = dbmod.sqlite3.connect(dbmod.DB_PATH)
        self.assertEqual(con.execute("SELECT status, changed_by FROM order_status_history WHERE order_id=?", (self.order,)).fetchone(), ("in_transit", self.admin))
        con.close()

    def test_invalid_status_and_missing_orders(self):
        self.login("admin@example.com")
        self.assertEqual(self.client.patch(f"/api/admin/orders/{self.order}/status", json={"status": "flying"}).status_code, 400)
        self.assertEqual(self.client.patch("/api/admin/orders/9999/status", json={"status": "pending"}).status_code, 404)

    def test_assign_reassign_and_validate_couriers(self):
        self.login("admin@example.com")
        path = f"/api/admin/orders/{self.order}/courier"
        first = self.client.patch(path, json={"courier_id": self.courier})
        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.get_json()["order"]["assigned_courier_name"], "Courier One")
        second = self.client.patch(path, json={"courier_id": self.courier2})
        self.assertEqual(second.status_code, 200)
        self.assertEqual(second.get_json()["order"]["assigned_courier_name"], "Courier Two")
        self.assertEqual(self.client.patch(path, json={"courier_id": self.customer}).status_code, 404)
        self.assertEqual(self.client.patch(path, json={"courier_id": "2"}).status_code, 400)
        self.assertEqual(self.client.patch(f"/api/admin/orders/{self.completed}/courier", json={"courier_id": self.courier}).status_code, 409)
        self.assertEqual(self.client.patch("/api/admin/orders/9999/courier", json={"courier_id": self.courier}).status_code, 404)

    def test_admin_deletes_order_and_missing_order_is_404(self):
        self.login("admin@example.com")
        self.assertEqual(self.client.delete(f"/api/admin/orders/{self.order}").status_code, 200)
        self.assertEqual(self.client.delete(f"/api/admin/orders/{self.order}").status_code, 404)


if __name__ == "__main__":
    unittest.main()
