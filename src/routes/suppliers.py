from flask import Blueprint, request, jsonify

suppliers_bp = Blueprint("suppliers", __name__)

MOCK_SUPPLIERS = [
    {"id": "forn_1", "name": "Fornecedor A", "status": "online",  "last_sync_at": "2025-08-25T12:00:00Z"},
    {"id": "forn_2", "name": "Fornecedor B", "status": "offline", "last_sync_at": "2025-08-25T12:00:00Z"},
]

@suppliers_bp.route("/suppliers", methods=["GET"])
def list_suppliers():
    page = int(request.args.get("page", 1))
    page_size = int(request.args.get("page_size", 20))
    status = request.args.get("status")
    q = request.args.get("q")

    items = MOCK_SUPPLIERS
    if status:
        items = [s for s in items if s["status"] == status]
    if q:
        items = [s for s in items if q.lower() in s["name"].lower()]

    total = len(items)
    start = (page - 1) * page_size
    end = start + page_size

    return jsonify({
        "items": items[start:end],
        "page": page,
        "page_size": page_size,
        "total": total
    })

@suppliers_bp.route("/suppliers/<supplier_id>/status", methods=["GET"])
def supplier_status(supplier_id):
    s = next((x for x in MOCK_SUPPLIERS if x["id"] == supplier_id), None)
    if not s:
        return jsonify({"detail": "Not found"}), 404
    return jsonify({
        "id": supplier_id,
        "status": s["status"],
        "latency_ms": 123,
        "last_ok_at": s["last_sync_at"]
    })
