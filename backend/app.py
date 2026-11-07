import os

from flask import Flask, jsonify
from flask_cors import CORS

try:
    from .db import close_db, init_db
    from .features.auth.routes import auth_bp
    from .features.orders.routes import orders_bp
    from .features.courier.routes import courier_bp
    from .features.admin.routes import admin_bp
except ImportError:
    from db import close_db, init_db
    from features.auth.routes import auth_bp
    from features.orders.routes import orders_bp
    from features.courier.routes import courier_bp
    from features.admin.routes import admin_bp


def create_app():
    app = Flask(__name__)
    cookie_origins = [
        origin.strip()
        for origin in os.environ.get(
            "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
        ).split(",")
        if origin.strip()
    ]
    CORS(
        app,
        resources={r"/api/*": {"origins": cookie_origins}},
        supports_credentials=True,
    )
    app.teardown_appcontext(close_db)
    app.register_blueprint(auth_bp)
    app.register_blueprint(orders_bp)
    app.register_blueprint(courier_bp)
    app.register_blueprint(admin_bp)

    @app.get("/api/health")
    def health():
        return jsonify({"status": "ok"})

    return app


app = create_app()


if __name__ == "__main__":
    init_db()
    app.run(host="127.0.0.1", port=5000, debug=True)
