# src/utils/debug_routes.py
import os
from flask import jsonify

SAFE_ENV_KEYS = {"RENDER", "PYTHON_VERSION"}

def register_debug_routes(app):
    """
    Habilita endpoints de debug quando DEBUG_ROUTES=1.
    REMOVA a flag depois do diagnóstico.
    """
    if os.getenv("DEBUG_ROUTES") != "1":
        return

    @app.get("/api/_routes")
    def _routes():
        out = []
        for rule in app.url_map.iter_rules():
            methods = sorted(m for m in rule.methods if m in {
                "GET","POST","PUT","DELETE","PATCH","OPTIONS","HEAD"
            })
            out.append({"rule": str(rule), "endpoint": rule.endpoint, "methods": methods})
        out.sort(key=lambda r: r["rule"])
        return jsonify(out)

    @app.get("/api/health/full")
    def _health_full():
        bps = sorted(app.blueprints.keys())
        env = {k: os.getenv(k) for k in SAFE_ENV_KEYS if os.getenv(k)}
        return jsonify({"status": "ok", "blueprints": bps, "env": env})
