# src/blueprints/suppliers.py
from flask import Blueprint, jsonify, request
from ..models import db, Supplier

suppliers_bp = Blueprint("suppliers", __name__, url_prefix="/api/suppliers")

def _serialize(s: Supplier):
    return {"id": s.id, "name": s.name, "email": s.email, "phone": s.phone}

@suppliers_bp.get("/")
def list_suppliers():
    q = Supplier.query.order_by(Supplier.id.desc())
    items = [_serialize(s) for s in q.limit(200).all()]
    return jsonify({"items": items, "total": q.count()})

@suppliers_bp.post("/")
def create_supplier():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "Campo obrigatório: name"}), 400
    s = Supplier(name=name, email=(data.get("email") or "").strip(), phone=(data.get("phone") or "").strip())
    db.session.add(s)
    db.session.commit()
    return jsonify(_serialize(s) | {"id": s.id}), 201

@suppliers_bp.get("/<int:supplier_id>")
def get_supplier(supplier_id: int):
    s = Supplier.query.get_or_404(supplier_id)
    return jsonify(_serialize(s))

@suppliers_bp.put("/<int:supplier_id>")
def update_supplier(supplier_id: int):
    s = Supplier.query.get_or_404(supplier_id)
    data = request.get_json(silent=True) or {}
    if "name" in data: s.name = (data["name"] or "").strip()
    if "email" in data: s.email = (data["email"] or "").strip()
    if "phone" in data: s.phone = (data["phone"] or "").strip()
    db.session.commit()
    return jsonify(_serialize(s))

@suppliers_bp.delete("/<int:supplier_id>")
def delete_supplier(supplier_id: int):
    s = Supplier.query.get_or_404(supplier_id)
    db.session.delete(s)
    db.session.commit()
    return jsonify({"deleted": supplier_id})
