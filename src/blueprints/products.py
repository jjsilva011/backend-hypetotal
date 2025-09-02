# C:\Users\jails\OneDrive\Desktop\Backend HypeTotal\src\blueprints\products.py
from flask import Blueprint, request, jsonify
from sqlalchemy import or_, asc, desc, func
from src.models import db, Product

bp = Blueprint("products", __name__, url_prefix="/api/products")

def product_to_dict(p: Product):
    return {
        "id": p.id,
        "sku": p.sku,
        "name": p.name,
        "description": p.description or "",
        "price": float(p.price or 0),
        "stock": int(p.stock or 0),  # <— NOVO
    }

@bp.route("/", methods=["GET"])
def list_products():
    page = max(int(request.args.get("page", 1)), 1)
    per_page = max(min(int(request.args.get("per_page", 10)), 50), 1)
    search = (request.args.get("search") or "").strip()
    sort_by = (request.args.get("sort_by") or "name").lower()
    sort_dir = (request.args.get("sort_dir") or "asc").lower()

    q = Product.query
    if search:
        like = f"%{search}%"
        q = q.filter(or_(Product.name.ilike(like), Product.description.ilike(like), Product.sku.ilike(like)))

    sort_map = {"name": Product.name, "price": Product.price, "id": Product.id, "sku": Product.sku, "stock": Product.stock}
    col = sort_map.get(sort_by, Product.name)
    q = q.order_by(asc(col) if sort_dir == "asc" else desc(col))

    pag = q.paginate(page=page, per_page=per_page, error_out=False)
    return jsonify({
        "products": [product_to_dict(p) for p in pag.items],
        "page": pag.page,
        "per_page": pag.per_page,
        "pages": pag.pages,
        "total": pag.total,
    })

# aceita POST e GET
@bp.route("/seed/", methods=["POST", "GET"])
def seed_products():
    try:
        n = int(request.args.get("n", 20))
    except Exception:
        n = 20
    n = max(1, min(n, 200))

    start = (db.session.query(func.coalesce(func.max(Product.id), 0)).scalar() or 0)

    for i in range(n):
        idx = start + i + 1
        db.session.add(Product(
            sku=f"DEMO-{idx:05d}",
            name=f"Produto Demo {idx}",
            description="Produto de demonstração para catálogo.",
            price=round(9.9 + idx * 10, 2),
            stock=(idx * 3) % 50 + 5,  # <— envia valor para NOT NULL
        ))
    db.session.commit()
    return jsonify({"created": n}), 201

@bp.route("/<int:pid>/", methods=["GET"])
def get_product(pid):
    p = Product.query.get_or_404(pid)
    return jsonify(product_to_dict(p))

@bp.route("/", methods=["POST"])
def create_product():
    data = request.get_json() or {}
    name = (data.get("name") or "").strip()
    sku = (data.get("sku") or "").strip()
    if not name or not sku:
        return jsonify({"error": "name and sku are required"}), 400
    p = Product(
        sku=sku,
        name=name,
        description=(data.get("description") or "").strip(),
        price=float(data.get("price") or 0),
        stock=int(data.get("stock") or 0),  # <— NOVO
    )
    db.session.add(p)
    db.session.commit()
    return jsonify(product_to_dict(p)), 201

@bp.route("/<int:pid>/", methods=["PUT"])
def update_product(pid):
    p = Product.query.get_or_404(pid)
    data = request.get_json() or {}
    if "sku" in data:
        p.sku = (data.get("sku") or "").strip()
    if "name" in data:
        p.name = (data.get("name") or "").strip()
    if "description" in data:
        p.description = (data.get("description") or "").strip()
    if "price" in data:
        p.price = float(data.get("price") or 0)
    if "stock" in data:  # <— NOVO
        p.stock = int(data.get("stock") or 0)
    db.session.commit()
    return jsonify(product_to_dict(p))

@bp.route("/<int:pid>/", methods=["DELETE"])
def delete_product(pid):
    p = Product.query.get_or_404(pid)
    db.session.delete(p)
    db.session.commit()
    return jsonify({"deleted": pid})

