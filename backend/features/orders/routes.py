from datetime import datetime, timezone

from flask import Blueprint, g, jsonify

try:
    from ...auth_utils import auth_required, error, parse_json
    from ...db import get_db
except ImportError:
    from auth_utils import auth_required, error, parse_json
    from db import get_db

orders_bp = Blueprint("orders", __name__, url_prefix="/api/orders")


@orders_bp.post("")
@auth_required
def create_order():
    data = parse_json()
    pickup = str(data.get("pickup_location", "")).strip()
    dropoff = str(data.get("dropoff_location", "")).strip()
    details = str(data.get("package_details", "")).strip()
    delivery_time = str(data.get("delivery_time", "")).strip()

    errors = {}
    if not pickup:
        errors["pickup_location"] = "Pickup location is required."
    if not dropoff:
        errors["dropoff_location"] = "Drop-off location is required."
    if not details:
        errors["package_details"] = "Package details are required."
    if not delivery_time:
        errors["delivery_time"] = "Delivery time is required."
    else:
        try:
            scheduled = datetime.fromisoformat(delivery_time)
            if scheduled.tzinfo is None:
                scheduled = scheduled.replace(tzinfo=timezone.utc)
            if scheduled <= datetime.now(timezone.utc):
                errors["delivery_time"] = "Delivery time must be in the future."
            delivery_time = scheduled.astimezone(timezone.utc).isoformat(
                timespec="minutes"
            )
        except ValueError:
            errors["delivery_time"] = "Delivery time must be a valid date and time."

    if errors:
        return error("Bad request", 400)

    db = get_db()
    cursor = db.execute(
        """
        INSERT INTO orders
            (user_id, pickup_location, dropoff_location, package_details, delivery_time)
        VALUES (?, ?, ?, ?, ?)
        """,
        (g.user["id"], pickup, dropoff, details, delivery_time),
    )
    db.commit()
    row = db.execute(
        "SELECT * FROM orders WHERE id = ?", (cursor.lastrowid,)
    ).fetchone()

    return jsonify({"message": "Order created successfully", "order": dict(row)}), 201


@orders_bp.get("")
@auth_required
def list_orders():
    rows = get_db().execute(
        "SELECT * FROM orders WHERE user_id = ? ORDER BY created_at DESC, id DESC",
        (g.user["id"],),
    ).fetchall()
    return jsonify({"orders": [dict(row) for row in rows]})


@orders_bp.get("/<int:order_id>")
@auth_required
def get_order(order_id: int):
    row = get_db().execute(
        "SELECT * FROM orders WHERE id = ? AND user_id = ?",
        (order_id, g.user["id"]),
    ).fetchone()
    if row is None:
        return error("Order not found", 404)
    return jsonify({"order": dict(row)})

@orders_bp.post("/<int:order_id>/cancel")
@auth_required
def cancel_order(order_id: int):
    db = get_db()
    row = db.execute(
        "SELECT id, status FROM orders WHERE id = ? AND user_id = ?",
        (order_id, g.user["id"]),
    ).fetchone()

    if row is None:
        return error("Order not found", 404)
    if row["status"] != "pending":
        return error("Only pending orders can be cancelled", 400)

    db.execute("UPDATE orders SET status = 'cancelled' WHERE id = ?", (order_id,))
    db.commit()

    updated = db.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
    return jsonify({"message": "Order cancelled", "order": dict(updated)})
