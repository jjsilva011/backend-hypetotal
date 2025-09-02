import os
import sys
from flask import Flask, send_from_directory
from flask_cors import CORS
from src.models.user import db

# Corrige sys.path para imports do pacote src/*
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

def _normalize_db_url(url: str) -> str:
    """Garante uso do driver psycopg3 na URL do Postgres."""
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg://", 1)
    if url.startswith("postgresql://") and "+psycopg" not in url:
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url

app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), 'static'))
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'hype_total_secret_key_2025')

# ✅ CORS liberando só seu domínio
CORS(app, resources={
    r"/api/*": {
        "origins": [
            "https://hypetotal.com",
            "https://www.hypetotal.com",
        ]
    }
})

# ✅ Configuração do banco (Render usa PostgreSQL, local usa SQLite)
DEFAULT_SQLITE = f"sqlite:///{os.path.join(os.path.dirname(__file__), 'database', 'app.db')}"
raw_db_url = os.getenv("SQLALCHEMY_DATABASE_URI") or os.getenv("DATABASE_URL") or DEFAULT_SQLITE
app.config['SQLALCHEMY_DATABASE_URI'] = _normalize_db_url(raw_db_url)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {"pool_pre_ping": True}

db.init_app(app)
with app.app_context():
    # cria pasta do sqlite se necessário
    if app.config['SQLALCHEMY_DATABASE_URI'].startswith("sqlite:///"):
        os.makedirs(os.path.join(os.path.dirname(__file__), 'database'), exist_ok=True)
    db.create_all()

# ✅ Importa e registra blueprints
from src.routes.user import user_bp
from src.routes.connectors import connectors_bp
from src.routes.aliexpress_setup import aliexpress_bp
from src.routes.demo_setup import demo_bp
from src.routes.cj_setup import cj_bp
from src.routes.spocket_setup import spocket_bp
from src.routes.ecommerce import ecommerce_bp
from src.blueprints.products import bp as products_bp  # <- importante para /api/products/*

app.register_blueprint(user_bp, url_prefix='/api')
app.register_blueprint(connectors_bp, url_prefix='/api')
app.register_blueprint(aliexpress_bp, url_prefix='/api')
app.register_blueprint(demo_bp, url_prefix='/api')
app.register_blueprint(cj_bp, url_prefix='/api')
app.register_blueprint(spocket_bp, url_prefix='/api')
app.register_blueprint(ecommerce_bp, url_prefix='/api')
app.register_blueprint(products_bp, url_prefix='/api/products')

# ✅ Health Check
@app.get('/api/health')
def health_check():
    return {'status': 'healthy', 'service': 'Hype Total Backend'}, 200

# ✅ Roteamento do frontend — não captura caminhos de API
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    if path.startswith('api/'):
        return "Not Found", 404
    static_folder_path = app.static_folder
    if static_folder_path and path and os.path.exists(os.path.join(static_folder_path, path)):
        return send_from_directory(static_folder_path, path)
    index_path = os.path.join(static_folder_path, 'index.html')
    if os.path.exists(index_path):
        return send_from_directory(static_folder_path, 'index.html')
    return "index.html not found", 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv("PORT", "5000")), debug=True)


