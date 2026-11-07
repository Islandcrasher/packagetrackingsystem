import re

from flask import Blueprint, g, jsonify
from werkzeug.security import check_password_hash, generate_password_hash

try:
    from ...auth_utils import (
        COOKIE_SECURE,
        auth_required,
        auth_response,
        create_token,
        error,
        parse_json,
        user_public,
    )
    from ...db import get_db
except ImportError:
    from auth_utils import (
        COOKIE_SECURE,
        auth_required,
        auth_response,
        create_token,
        error,
        parse_json,
        user_public,
    )
    from db import get_db

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@auth_bp.post("/register")
def register():
    data = parse_json()
    name = str(data.get("name", "")).strip()
    email = str(data.get("email", "")).strip().lower()
    phone = str(data.get("phone", "")).strip()
    password = str(data.get("password", ""))

    errors = {}
    if len(name) < 2:
        errors["name"] = "Name must be at least 2 characters."
    if not EMAIL_RE.match(email):
        errors["email"] = "Enter a valid email address."
    digits = re.sub(r"\D", "", phone)
    if len(digits) < 7 or len(digits) > 15:
        errors["phone"] = "Enter a valid phone number (7-15 digits)."
    if len(password) < 8:
        errors["password"] = "Password must be at least 8 characters."
    if errors:
        return error("Unable to create account", 400)

    db = get_db()
    exists = db.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
    if exists:
        return error("Unable to create account", 400)

    cursor = db.execute(
        "INSERT INTO users (name, email, phone, password_hash) VALUES (?, ?, ?, ?)",
        (name, email, phone, generate_password_hash(password)),
    )
    db.commit()
    row = db.execute(
        "SELECT id, name, email, phone FROM users WHERE id = ?", (cursor.lastrowid,)
    ).fetchone()

    return auth_response(
        {
            "message": "Account created successfully",
            "user": user_public(row),
        },
        create_token(row["id"]),
        201,
    )


@auth_bp.post("/login")
def login():
    data = parse_json()
    email = str(data.get("email", "")).strip().lower()
    password = str(data.get("password", ""))

    if not email or not password:
        return error("Invalid credentials", 401)

    row = get_db().execute(
        "SELECT id, name, email, phone, password_hash FROM users WHERE email = ?",
        (email,),
    ).fetchone()
    if row is None or not check_password_hash(row["password_hash"], password):
        return error("Invalid credentials", 401)

    return auth_response(
        {
            "message": "Logged in successfully",
            "user": user_public(row),
        },
        create_token(row["id"]),
    )


@auth_bp.post("/logout")
def logout():
    response = jsonify({"message": "Logged out successfully"})
    response.delete_cookie(
        "swiftship_token",
        path="/api",
        secure=COOKIE_SECURE,
        httponly=True,
        samesite="Lax",
    )
    return response


@auth_bp.get("/me")
@auth_required
def me():
    return jsonify({"user": g.user})
