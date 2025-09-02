from flask import Blueprint, request, jsonify

orders_bp = Blueprint("orders", __name__)

# mock simples
MOCK_ORDERS = [
    {
        "id": f"ord_{i}",
        "number": f"{100000+i}",
        "status": "paid" if i % 3 else "pending",
        "total": round(99.9 + i, 2),
        "currency": "BRL",
        "channel": "shopify" if i % 2 else "magento",
        "customer_name": f"Cliente {i}",
        "created_at": "2025-08-24T14:33:10Z",
    }
    for i in range(1, 101)
]

@orders_bp.route("/orders", methods=["GET"])
def list_orders():
    page = int(request.args.get("page", 1))
    page_size = int(request.args.get("page_size", 20))
    status = request.args.get("status")
    channel = request.args.get("channel")
    q = request.args.get("q")

    items = MOCK_ORDERS
    if status:
        items = [o for o in items if o["status"] == status]
    if channel:
        items = [o for o in items if o["channel"] == channel]
    if q:
        items = [o for o in items if q.lower() in o["customer_name"].lower() or q in o["number"]]

    total = len(items)
    start = (page - 1) * page_size
    end = start + page_size

    return jsonify({
        "items": items[start:end],
        "page": page,
        "page_size": page_size,
        "total": total
    })

@orders_bp.route("/orders/<order_id>", methods=["GET"])
def get_order(order_id):
    for o in MOCK_ORDERS:
        if o["id"] == order_id:
            return jsonify(o)
    return jsonify({"detail": "Not found"}), 404
