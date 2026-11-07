"""Admin-only order management and courier assignment APIs."""
from functools import wraps

from flask import Blueprint, g, jsonify

try:
    from ...auth_utils import auth_required, error, parse_json
    from ...db import get_db
except ImportError:
    from auth_utils import auth_required, error, parse_json
    from db import get_db

admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")
ORDER_STATUSES = {"pending", "accepted", "picked_up", "in_transit", "delivered", "cancelled"}
ORDER_SELECT = """
    SELECT o.*, customer.name AS customer_name, customer.email AS customer_email,
           customer.phone AS customer_phone, courier.name AS assigned_courier_name,
           courier.email AS assigned_courier_email, courier.phone AS assigned_courier_phone
    FROM orders o
    JOIN users customer ON customer.id = o.user_id
    LEFT JOIN users courier ON courier.id = o.courier_id AND courier.role = 'courier'
"""


def admin_required(fn):
    @auth_required
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if g.user.get("role") != "admin":
            return error("Administrator access required", 403)
        return fn(*args, **kwargs)

    return wrapper


@admin_bp.get("/orders")
@admin_required
def list_orders():
    rows = get_db().execute(ORDER_SELECT + " ORDER BY o.created_at DESC, o.id DESC").fetchall()
    return jsonify({"orders": [dict(row) for row in rows]})


@admin_bp.get("/couriers")
@admin_required
def list_couriers():
    rows = get_db().execute(
        "SELECT id, name, email, phone FROM users WHERE role = 'courier' ORDER BY name, id"
    ).fetchall()
    return jsonify({"couriers": [dict(row) for row in rows]})


@admin_bp.patch("/orders/<int:order_id>/status")
@admin_required
def update_order_status(order_id: int):
    data = parse_json()
    status = data.get("status")
    if not isinstance(status, str) or status.strip().lower() not in ORDER_STATUSES:
        return error("Invalid status", 400, {"status": "Choose a supported order status."})
    status = status.strip().lower()
    db = get_db()
    row = db.execute("SELECT id, status FROM orders WHERE id = ?", (order_id,)).fetchone()
    if row is None:
        return error("Order not found", 404)
    try:
        if row["status"] != status:
            db.execute("UPDATE orders SET status = ? WHERE id = ?", (status, order_id))
            db.execute(
                "INSERT INTO order_status_history (order_id, status, changed_by) VALUES (?, ?, ?)",
                (order_id, status, g.user["id"]),
            )
            db.commit()
        updated = db.execute(ORDER_SELECT + " WHERE o.id = ?", (order_id,)).fetchone()
        return jsonify({"order": dict(updated)})
    except Exception:
        db.rollback()
        return error("Unable to update order status", 500)


@admin_bp.patch("/orders/<int:order_id>/courier")
@admin_required
def assign_courier(order_id: int):
    data = parse_json()
    courier_id = data.get("courier_id")
    if isinstance(courier_id, bool) or not isinstance(courier_id, int) or courier_id <= 0:
        return error("Invalid courier", 400, {"courier_id": "Provide a valid courier id."})
    db = get_db()
    order = db.execute("SELECT id, status FROM orders WHERE id = ?", (order_id,)).fetchone()
    if order is None:
        return error("Order not found", 404)
    if order["status"] in ("delivered", "cancelled"):
        return error("Completed or cancelled orders cannot be assigned", 409)
    courier = db.execute(
        "SELECT id FROM users WHERE id = ? AND role = 'courier'", (courier_id,)
    ).fetchone()
    if courier is None:
        return error("Courier not found", 404)
    try:
        db.execute(
            "UPDATE orders SET courier_id = ?, courier_name = NULL, courier_phone = NULL WHERE id = ?",
            (courier_id, order_id),
        )
        db.commit()
        updated = db.execute(ORDER_SELECT + " WHERE o.id = ?", (order_id,)).fetchone()
        return jsonify({"message": "Courier assigned", "order": dict(updated)})
    except Exception:
        db.rollback()
        return error("Unable to assign courier", 500)


@admin_bp.delete("/orders/<int:order_id>")
@admin_required
def delete_order(order_id: int):
    db = get_db()
    try:
        cursor = db.execute("DELETE FROM orders WHERE id = ?", (order_id,))
        if cursor.rowcount != 1:
            db.rollback()
            return error("Order not found", 404)
        db.commit()
        return jsonify({"message": "Order deleted", "order_id": order_id})
    except Exception:
        db.rollback()
        return error("Unable to delete order", 500)
