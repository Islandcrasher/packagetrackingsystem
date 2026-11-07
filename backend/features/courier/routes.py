"""Courier features.

Feature #7 - Assigned Orders (list, accept, decline)
Feature #8 - Update Order Status (picked_up -> in_transit -> delivered)

Status life-cycle of an order:

    pending --accept--> accepted --> picked_up --> in_transit --> delivered
       |
       +--decline--> (courier removed, order goes back to the admin as 'pending')

An order is assigned to a courier by the admin (feature #10) which sets
orders.courier_id. Everything here only ever touches orders assigned to the
logged-in courier.
"""
from functools import wraps

from flask import Blueprint, g, jsonify

try:
    from ...auth_utils import auth_required, error, parse_json
    from ...db import get_db
except ImportError:
    from auth_utils import auth_required, error, parse_json
    from db import get_db

courier_bp = Blueprint("courier", __name__, url_prefix="/api/courier")

# Allowed forward moves for the courier (strictly one step at a time).
NEXT_STATUS = {
    "accepted": "picked_up",
    "picked_up": "in_transit",
    "in_transit": "delivered",
}
UPDATABLE_STATUSES = set(NEXT_STATUS.values())

ORDER_SELECT = """
    SELECT o.*, u.name AS customer_name, u.phone AS customer_phone
    FROM orders o
    JOIN users u ON u.id = o.user_id
"""


def roles_required(*roles):
    """Allow only users whose role is in `roles` (runs after authentication)."""

    def decorator(fn):
        @auth_required
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if g.user.get("role") not in roles:
                return error("You do not have permission to do this", 403)
            return fn(*args, **kwargs)

        return wrapper

    return decorator


courier_required = roles_required("courier")


def _assigned_order(order_id: int):
    """The order, only if it is assigned to the logged-in courier."""
    return (
        get_db()
        .execute(
            ORDER_SELECT + " WHERE o.id = ? AND o.courier_id = ?",
            (order_id, g.user["id"]),
        )
        .fetchone()
    )


def _record_history(db, order_id: int, status: str) -> None:
    db.execute(
        "INSERT INTO order_status_history (order_id, status, changed_by) "
        "VALUES (?, ?, ?)",
        (order_id, status, g.user["id"]),
    )


def _history(order_id: int) -> list:
    rows = get_db().execute(
        """
        SELECT h.id, h.status, h.changed_at, u.name AS changed_by_name
        FROM order_status_history h
        LEFT JOIN users u ON u.id = h.changed_by
        WHERE h.order_id = ?
        ORDER BY h.id ASC
        """,
        (order_id,),
    ).fetchall()
    return [dict(row) for row in rows]


# --------------------------------------------------------------------------
# Feature #7 - Assigned Orders
# --------------------------------------------------------------------------
@courier_bp.get("/<int:courier_id>/orders")
@roles_required("courier", "admin")
def list_assigned_orders(courier_id: int):
    """Orders assigned to the courier with this id."""
    if g.user["role"] == "courier" and g.user["id"] != courier_id:
        return error("You can only view your own assigned orders", 403)

    db = get_db()
    courier = db.execute(
        "SELECT id FROM users WHERE id = ? AND role = 'courier'", (courier_id,)
    ).fetchone()
    if courier is None:
        return error("Courier not found", 404)

    rows = db.execute(
        ORDER_SELECT + " WHERE o.courier_id = ? ORDER BY o.created_at DESC, o.id DESC",
        (courier_id,),
    ).fetchall()
    return jsonify({"orders": [dict(row) for row in rows]})


@courier_bp.get("/orders/<int:order_id>")
@courier_required
def get_assigned_order(order_id: int):
    row = _assigned_order(order_id)
    if row is None:
        return error("Order not found", 404)
    return jsonify({"order": dict(row), "history": _history(order_id)})


@courier_bp.post("/orders/<int:order_id>/accept")
@courier_required
def accept_order(order_id: int):
    row = _assigned_order(order_id)
    if row is None:
        return error("Order not found", 404)
    if row["status"] != "pending":
        return error(f"Only pending orders can be accepted (this order is {row['status']})", 409)

    db = get_db()
    cursor = db.execute(
        """
        UPDATE orders
        SET status = 'accepted', courier_name = ?, courier_phone = ?
        WHERE id = ? AND courier_id = ? AND status = 'pending'
        """,
        (g.user["name"], g.user["phone"], order_id, g.user["id"]),
    )
    if cursor.rowcount != 1:
        db.rollback()
        return error("Order was changed by someone else, please refresh", 409)
    _record_history(db, order_id, "accepted")
    db.commit()

    return jsonify({"message": "Order accepted", "order": dict(_assigned_order(order_id))})


@courier_bp.post("/orders/<int:order_id>/decline")
@courier_required
def decline_order(order_id: int):
    row = _assigned_order(order_id)
    if row is None:
        return error("Order not found", 404)
    if row["status"] != "pending":
        return error(f"Only pending orders can be declined (this order is {row['status']})", 409)

    db = get_db()
    cursor = db.execute(
        """
        UPDATE orders
        SET courier_id = NULL, courier_name = NULL, courier_phone = NULL
        WHERE id = ? AND courier_id = ? AND status = 'pending'
        """,
        (order_id, g.user["id"]),
    )
    if cursor.rowcount != 1:
        db.rollback()
        return error("Order was changed by someone else, please refresh", 409)
    _record_history(db, order_id, "declined")
    db.commit()

    # The order is no longer assigned to this courier (it goes back to the admin).
    return jsonify({"message": "Order declined", "order_id": order_id})


# --------------------------------------------------------------------------
# Feature #8 - Update Order Status
# --------------------------------------------------------------------------
@courier_bp.patch("/orders/<int:order_id>/status")
@courier_required
def update_order_status(order_id: int):
    data = parse_json()
    new_status = str(data.get("status", "")).strip().lower()

    if new_status not in UPDATABLE_STATUSES:
        return (
            jsonify(
                {
                    "error": "Invalid status",
                    "details": {
                        "status": "Status must be one of: picked_up, in_transit, delivered"
                    },
                }
            ),
            400,
        )

    row = _assigned_order(order_id)
    if row is None:
        return error("Order not found", 404)

    current = row["status"]
    if current == "pending":
        return error("Accept the order before updating its status", 409)
    if current == "cancelled":
        return error("This order was cancelled by the customer", 409)
    if current == "delivered":
        return error("This order has already been delivered", 409)
    if NEXT_STATUS.get(current) != new_status:
        expected = NEXT_STATUS.get(current)
        return error(
            f"Invalid status change: '{current}' -> '{new_status}'. Next allowed status is '{expected}'",
            409,
        )

    db = get_db()
    cursor = db.execute(
        "UPDATE orders SET status = ? WHERE id = ? AND courier_id = ? AND status = ?",
        (new_status, order_id, g.user["id"], current),
    )
    if cursor.rowcount != 1:
        db.rollback()
        return error("Order was changed by someone else, please refresh", 409)
    _record_history(db, order_id, new_status)
    db.commit()

    return jsonify(
        {
            "message": f"Order marked as {new_status}",
            "order": dict(_assigned_order(order_id)),
            "history": _history(order_id),
        }
    )
