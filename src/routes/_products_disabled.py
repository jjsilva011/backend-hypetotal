from flask import Blueprint, request, jsonify

products_bp = Blueprint("products", __name__)

MOCK_PRODUCTS = [
    {
        "id": f"prod_{i}",
        "sku": f"SKU-{i:04d}",
        "name": f"Produto {i}",
        "price": round(49.9 + i, 2),
        "image_url": f"https://picsum.photos/seed/{i}/400/400",
        "supplier_id": "forn_1" if i % 2 else "forn_2",
        "in_stock": bool(i % 3),
    }
    for i in range(1, 97)
]

@products_bp.route("/products", methods=["GET"])
def list_products():
    page = int(request.args.get("page", 1))
    page_size = int(request.args.get("page_size", 24))
    q = request.args.get("q")
    supplier_id = request.args.get("supplier_id")
    in_stock = request.args.get("in_stock")  # "true"/"false" opcional

    items = MOCK_PRODUCTS
    if q:
        items = [p for p in items if q.lower() in p["name"].lower() or q.lower() in p["sku"].lower()]
    if supplier_id:
        items = [p for p in items if p["supplier_id"] == supplier_id]
    if in_stock is not None:
        if in_stock.lower() in ("1", "true", "yes"):
            items = [p for p in items if p["in_stock"] is True]
        if in_stock.lower() in ("0", "false", "no"):
            items = [p for p in items if p["in_stock"] is False]

    total = len(items)
    start = (page - 1) * page_size
    end = start + page_size

    return jsonify({
        "items": items[start:end],
        "page": page,
        "page_size": page_size,
        "total": total
    })

@products_bp.route("/products/<product_id>", methods=["GET"])
def get_product(product_id):
    for p in MOCK_PRODUCTS:
        if p["id"] == product_id:
            return jsonify(p)
    return jsonify({"detail": "Not found"}), 404
