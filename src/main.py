# C:\Users\jails\OneDrive\Desktop\Backend HypeTotal\src\main.py
import os
from flask import Flask, jsonify, request
from flask_cors import CORS
from sqlalchemy import inspect, text

from src.models import db
from src.blueprints import products as products_bp

def create_app():
    app = Flask(__name__)
    app.url_map.strict_slashes = False

    db_url = os.getenv("DATABASE_URL")
    if db_url:
        app.config["SQLALCHEMY_DATABASE_URI"] = db_url
    else:
        base = os.path.abspath(os.path.dirname(__file__))
        app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{os.path.join(base, 'database', 'app.db')}"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    allowed = os.getenv("ALLOWED_CORS_ORIGINS")
    if allowed:
        origins = [o.strip() for o in allowed.split(",") if o.strip()]
        CORS(app, resources={r"/api/*": {"origins": origins}})
    else:
        CORS(app, resources={r"/api/*": {"origins": "*"}})

    db.init_app(app)

    # Cria/ajusta schema sem Alembic
    with app.app_context():
        db.create_all()
        insp = inspect(db.engine)
        try:
            cols = {c["name"] for c in insp.get_columns("products")}
        except Exception:
            cols = set()

        if "description" not in cols:
            db.session.execute(text("ALTER TABLE products ADD COLUMN description TEXT"))
            db.session.commit()

        if "sku" not in cols:
            db.session.execute(text("ALTER TABLE products ADD COLUMN sku VARCHAR(64)"))
            db.session.commit()

        if "stock" not in cols:
            # Em SQLite, DEFAULT preenche linhas existentes; ainda assim normalizamos depois.
            db.session.execute(text("ALTER TABLE products ADD COLUMN stock INTEGER DEFAULT 0"))
            db.session.commit()

        # Normalizações para dados antigos
        # Preenche SKU vazio
        dialect = db.engine.dialect.name
        if "sku" in cols or True:
            if dialect == "sqlite":
                db.session.execute(
                    text("UPDATE products SET sku = 'SKU-' || printf('%03d', id) WHERE sku IS NULL OR sku = ''")
                )
            else:
                db.session.execute(
                    text("UPDATE products SET sku = 'SKU-' || LPAD(id::text, 3, '0') WHERE (sku IS NULL OR sku = '')")
                )
            db.session.commit()

        # Garante stock não-nulo
        db.session.execute(text("UPDATE products SET stock = 0 WHERE stock IS NULL"))
        db.session.commit()

    @app.get("/api/health")
    def health():
        return jsonify({"service": "Hype Total Backend", "status": "healthy"})

    app.register_blueprint(products_bp.bp)

    @app.errorhandler(404)
    def not_found(e):
        if request.path.startswith("/api/"):
            return jsonify({"error": "Not Found", "path": request.path}), 404
        return e

    return app

app = create_app()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5001, debug=True)


















