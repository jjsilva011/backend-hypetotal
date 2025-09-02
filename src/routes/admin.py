from flask import Blueprint, jsonify, request

admin_bp = Blueprint("admin", __name__)

@admin_bp.route("/admin/stats", methods=["GET"])
def admin_stats():
    # opcional: ?range=7d|30d
    _range = request.args.get("range", "7d")
    return jsonify({
        "orders": 123,
        "revenue": 45678.9,
        "avg_ticket": 371.37,
        "top_channels": [
            {"name": "shopify", "orders": 85},
            {"name": "magento", "orders": 38},
        ],
        "range": _range
    })
