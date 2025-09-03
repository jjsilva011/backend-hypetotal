import os
import sys
from flask import Flask, send_from_directory, jsonify
from flask_cors import CORS

# garante import "src.*"
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# SQLAlchemy (instanciado em src/models/__init__.py)
from src.models import db  # <-- use o pacote, não "from src.models.user import db"

# Blueprints (novos)
from src.blueprints.products import bp as products_bp
from src.blueprints.orders import bp as orders_bp
from src.blueprints.suppliers import bp as suppliers_bp

# Blueprints antigos (se ainda usados)
from src.routes.user import user_bp
from src.routes.connectors import connectors_bp
from src.routes.aliexpress_setup import aliexpress_bp
from src.routes.demo_setup import demo_bp
from src.routes.cj_setup import cj_bp
from src.routes.spocket_setup import spocket_bp
from src.routes.ecommerce import ecommerce_bp


def _normalize_database_url(raw_url: str) -> str:
    """
    Render fornece DATABASE_URL tipo:
      - postgres://...  (precisa trocar para postgresql+psycopg://)
    Além disso, força SSL em produção.
    """
    if not raw_url:
        # SQLite local padrão (arquivo em src/database/app.db)
        return f"sqlite:///{os.path.join(os.path.dirname(__file__), 'database', 'app.db')}"
    url = raw_url
    # aceita "postgres://" e "postgresql://"
    if url.startswith("postgres://"):
        url = "postgresql+psycopg://" + url[len("postgres://"):]
    elif url.startswith("postgresql://"):
        # adiciona driver psycopg se não tiver
        if not url.startswith("postgresql+"):
            url = "postgresql+psycopg://" + url[len("postgresql://"):]
    # Render precisa SSL
    if "postgresql+psycopg://" in url and "sslmode=" not in url:
        sep = "&" if "?" in url else "?"
        url = f"{url}{sep}sslmode=require"
    return url


def create_app() -> Flask:
    app = Flask(
        __name__,
        static_folder=os.path.join(os.path.dirname(__file__), "static"),
        static_url_path="/"
    )
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "hype_total_secret_key_2025")

    # CORS somente para o seu domínio em /api/*
    CORS(app, resources={
        r"/api/*": {
            "origins": [
                "https://hypetotal.com",
                "https://www.hypetotal.com"
            ]
        }
    })

    # Banco
    raw_db_url = os.getenv("DATABASE_URL", "")
    app.config["SQLALCHEMY_DATABASE_URI"] = _normalize_database_url(raw_db_url)
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    db.init_app(app)

    # Cria tabelas se SQLite local
    with app.app_context():
        if app.config["SQLALCHEMY_DATABASE_URI"].startswith("sqlite:///"):
            os.makedirs(os.path.join(os.path.dirname(__file__), "database"), exist_ok=True)
        db.create_all()

    # Health check
    @app.route("/api/health", methods=["GET"])
    def health():
        return jsonify({"status": "healthy", "service": "Hype Total Backend"}), 200

    # Registra blueprints NOVOS (produtos tem /seed POST, / list em JSON, etc.)
    app.register_blueprint(products_bp, url_prefix="/api/products")
    app.register_blueprint(orders_bp, url_prefix="/api/orders")
    app.register_blueprint(suppliers_bp, url_prefix="/api/suppliers")

    # Registra os blueprints antigos (se ainda estiver usando)
    app.register_blueprint(user_bp, url_prefix="/api")
    app.register_blueprint(connectors_bp, url_prefix="/api")
    app.register_blueprint(aliexpress_bp, url_prefix="/api")
    app.register_blueprint(demo_bp, url_prefix="/api")
    app.register_blueprint(cj_bp, url_prefix="/api")
    app.register_blueprint(spocket_bp, url_prefix="/api")
    app.register_blueprint(ecommerce_bp, url_prefix="/api")

    # Serve frontend estático SEM engolir /api/*
    @app.route("/", defaults={"path": ""})
    @app.route("/<path:path>")
    def serve_frontend(path):
        # Não intercepta API
        if path.startswith("api/"):
            return ("Not Found", 404)

        static_root = app.static_folder
        if static_root:
            candidate = os.path.join(static_root, path)
            index_html = os.path.join(static_root, "index.html")
            if path and os.path.exists(candidate):
                return send_from_directory(static_root, path)
            if os.path.exists(index_html):
                return send_from_directory(static_root, "index.html")
        return ("index.html not found", 404)

    return app


# WSGI para gunicorn/render
app = create_app()

if __name__ == "__main__":
    # execução local
    app.run(host="127.0.0.1", port=5001, debug=True)


















