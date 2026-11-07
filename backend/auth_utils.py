import os
from datetime import datetime, timedelta, timezone
from functools import wraps

import jwt
from flask import g, jsonify, request

try:
    from .db import get_db
except ImportError:
    from db import get_db

TOKEN_TTL_HOURS = int(os.environ.get("TOKEN_TTL_HOURS", "24"))
SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me-in-production")
COOKIE_SECURE = os.environ.get("COOKIE_SECURE", "false").lower() in {
    "1",
    "true",
    "yes",
}


def error(message: str, status: int = 400, details: dict | None = None):
    body = {"error": message}
    if details:
        body["details"] = details
    return jsonify(body), status


def parse_json():
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}


def create_token(user_id: int) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(hours=TOKEN_TTL_HOURS),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")


def auth_response(body: dict, token: str, status: int = 200):
    response = jsonify(body)
    response.set_cookie(
        "swiftship_token",
        token,
        max_age=TOKEN_TTL_HOURS * 60 * 60,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite="Lax",
        path="/api",
    )
    return response, status


def user_public(row) -> dict:
    return {
        "id": row["id"],
        "name": row["name"],
        "email": row["email"],
        "phone": row["phone"],
    }


def auth_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        token = request.cookies.get("swiftship_token")
        if not token:
            return error("Authentication required", 401)
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
            user_id = int(payload["sub"])
        except jwt.ExpiredSignatureError:
            return error("Token has expired", 401)
        except (jwt.InvalidTokenError, KeyError, TypeError, ValueError):
            return error("Invalid token", 401)

        row = get_db().execute(
            "SELECT id, name, email, phone FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
        if row is None:
            return error("User no longer exists", 401)

        g.user = dict(row)
        return fn(*args, **kwargs)

    return wrapper
