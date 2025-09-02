# src/main.py (dentro de create_app, antes de db.init_app)
import os

def create_app():
    app = Flask(__name__)
    # ...

    db_url = os.getenv("DATABASE_URL")
    if db_url:
        # Render costuma fornecer "postgres://..." (ou "postgresql://...")
        # SQLAlchemy + psycopg 3 querem "postgresql+psycopg://..."
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql+psycopg://", 1)
        elif db_url.startswith("postgresql://"):
            db_url = db_url.replace("postgresql://", "postgresql+psycopg://", 1)

        app.config["SQLALCHEMY_DATABASE_URI"] = db_url
    else:
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///app.sqlite"

    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {"pool_pre_ping": True}

    db.init_app(app)

    with app.app_context():
        db.create_all()  # se você não estiver usando migrations

    # registre as blueprints /api/*
    from src.blueprints.products import bp as products_bp
    app.register_blueprint(products_bp, url_prefix="/api/products")

    @app.get("/api/health")
    def health():
        return {"service": "Hype Total Backend", "status": "healthy"}

    return app















