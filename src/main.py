import os
import sys
# DON'T CHANGE THIS !!!
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

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

app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), 'static'))
app.config['SECRET_KEY'] = 'hype_total_secret_key_2025'

# Habilita CORS para todas as rotas
CORS(app)

# Registra todos os blueprints
app.register_blueprint(user_bp, url_prefix='/api')
app.register_blueprint(connectors_bp, url_prefix='/api')
app.register_blueprint(aliexpress_bp, url_prefix='/api')
app.register_blueprint(demo_bp, url_prefix='/api')
app.register_blueprint(cj_bp, url_prefix='/api')
app.register_blueprint(spocket_bp, url_prefix='/api')
app.register_blueprint(ecommerce_bp, url_prefix='/api')

# Configuração do banco de dados
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(os.path.dirname(__file__), 'database', 'app.db')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

with app.app_context():
    db.create_all()

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    """Serve frontend files and handle SPA routing."""
    static_folder_path = app.static_folder
    if static_folder_path is None:
        return "Static folder not configured", 404

    if path != "" and os.path.exists(os.path.join(static_folder_path, path)):
        return send_from_directory(static_folder_path, path)
    else:
        index_path = os.path.join(static_folder_path, 'index.html')
        if os.path.exists(index_path):
            return send_from_directory(static_folder_path, 'index.html')
        else:
            return "index.html not found", 404

@app.route('/health')
def health_check():
    """Health check endpoint."""
    return {'status': 'healthy', 'service': 'Hype Total Backend'}, 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

