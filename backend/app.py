"""Flask application factory CookieKub."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, abort, g, jsonify, request, send_from_directory
from flask_cors import CORS

from .errors import ApiError
from .extensions import close_db, get_db
from .security import bearer_token, resolve_token
from .serializers import iso

FRONTEND_DIR = Path(__file__).resolve().parents[1] / "frontend"


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(__name__, static_folder=None)
    from .config import Config

    app.config.from_object(Config)
    if test_config:
        app.config.update(test_config)
    app.json.ensure_ascii = False

    CORS(
        app,
        resources={r"/api/*": {"origins": app.config["CORS_ORIGINS"]}},
        allow_headers=["Content-Type", "Authorization"],
        methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        supports_credentials=False,
        max_age=600,
    )

    app.teardown_appcontext(close_db)

    @app.before_request
    def load_current_user():
        g.user = None
        if not request.path.startswith("/api/") or request.method == "OPTIONS":
            return None
        token = bearer_token()
        if not token:
            return None
        user = resolve_token(get_db(), token)
        if not user:
            raise ApiError(401, "session_expired", "Сессия истекла. Войдите заново.")
        g.user = user
        return None

    @app.after_request
    def security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        if request.path.startswith("/api/"):
            response.headers.setdefault("Cache-Control", "no-store")
        return response

    @app.get("/api/health")
    def health():
        try:
            get_db().execute("SELECT 1").fetchone()
            db_ok = True
        except Exception:
            db_ok = False
        payload = {
            "status": "ok" if db_ok else "degraded",
            "db": db_ok,
            "time": iso(datetime.now(timezone.utc)),
            "app": "cookiekub",
        }
        return jsonify(payload), (200 if db_ok else 503)

    from . import admin, auth, catalog, maintenance, orders, tickets

    app.register_blueprint(auth.bp)
    app.register_blueprint(catalog.bp)
    app.register_blueprint(orders.bp)
    app.register_blueprint(tickets.bp)
    app.register_blueprint(admin.bp)
    app.register_blueprint(maintenance.bp)

    @app.errorhandler(ApiError)
    def handle_api_error(exc: ApiError):
        return jsonify(exc.to_dict()), exc.status

    @app.errorhandler(404)
    def not_found(_exc):
        if request.path.startswith("/api/"):
            return jsonify({"error": {"code": "not_found", "message": "Маршрут не найден"}}), 404
        page = FRONTEND_DIR / "404.html"
        if page.is_file():
            return send_from_directory(FRONTEND_DIR, "404.html"), 404
        return "404", 404

    @app.errorhandler(405)
    def method_not_allowed(_exc):
        if request.path.startswith("/api/"):
            return jsonify({"error": {"code": "method_not_allowed", "message": "Метод не разрешён"}}), 405
        return send_from_directory(FRONTEND_DIR, "404.html"), 404

    @app.errorhandler(500)
    def server_error(_exc):
        if request.path.startswith("/api/"):
            return jsonify({"error": {"code": "server_error", "message": "Внутренняя ошибка сервера"}}), 500
        page = FRONTEND_DIR / "500.html"
        if page.is_file():
            return send_from_directory(FRONTEND_DIR, "500.html"), 500
        return "500", 500

    @app.errorhandler(413)
    def too_large(_exc):
        return jsonify({"error": {"code": "too_large", "message": "Слишком большой запрос"}}), 413

    @app.get("/")
    def index():
        return send_from_directory(FRONTEND_DIR, "index.html")

    @app.get("/<path:filename>")
    def static_page(filename: str):
        if filename.startswith("api/"):
            abort(404)
        target = (FRONTEND_DIR / filename).resolve()
        try:
            target.relative_to(FRONTEND_DIR.resolve())
        except ValueError:
            return send_from_directory(FRONTEND_DIR, "404.html"), 404
        if target.is_file():
            return send_from_directory(FRONTEND_DIR, filename)
        return send_from_directory(FRONTEND_DIR, "404.html"), 404

    return app
