import os
import sys
from flask import Flask, send_from_directory
from flask_cors import CORS
from src.models.user import db
from src.routes.user import user_bp
from src.routes.connectors import connectors_bp
from src.routes.aliexpress_setup import aliexpress_bp
from src.routes.demo_setup import demo_bp
from src.routes.cj_setup import cj_bp
from src.routes.spocket_setup import spocket_bp
from src.routes.ecommerce import ecommerce_bp

# Corrige sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), 'static'))
app.config['SECRET_KEY'] = 'hype_total_secret_key_2025'

# ✅ CORS liberando só seu domínio
CORS(app, resources={
    r"/api/*": {
        "origins": [
            "https://hypetotal.com",
            "https://www.hypetotal.com"
        ]
    }
})

# Registra todos os blueprints
app.register_blueprint(user_bp, url_prefix='/api')
app.register_blueprint(connectors_bp, url_prefix='/api')
app.register_blueprint(aliexpress_bp, url_prefix='/api')
app.register_blueprint(demo_bp, url_prefix='/api')
app.register_blueprint(cj_bp, url_prefix='/api')
app.register_blueprint(spocket_bp, url_prefix='/api')
app.register_blueprint(ecommerce_bp, url_prefix='/api')

# ✅ Configuração do banco (Render usa PostgreSQL, local usa SQLite)
DEFAULT_SQLITE = f"sqlite:///{os.path.join(os.path.dirname(__file__), 'database', 'app.db')}"
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URL", DEFAULT_SQLITE)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

with app.app_context():
    db.create_all()

# ✅ Health Check
@app.route('/api/health')
def health_check():
    return {'status': 'healthy', 'service': 'Hype Total Backend'}, 200

# ✅ Roteamento do frontend (caso hospede junto)
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    static_folder_path = app.static_folder
    if static_folder_path and path != "" and os.path.exists(os.path.join(static_folder_path, path)):
        return send_from_directory(static_folder_path, path)
    else:
        index_path = os.path.join(static_folder_path, 'index.html')
        if os.path.exists(index_path):
            return send_from_directory(static_folder_path, 'index.html')
        return "index.html not found", 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

