# src/blueprints/orders.py
from flask import Blueprint, jsonify, request
from decimal import Decimal, InvalidOperation
from sqlalchemy.exc import IntegrityError
from ..models import db, Order

orders_bp = Blueprint("orders", __name__, url_prefix="/api/orders")

def _serialize(o: Order):
    return {
        "id": o.id,
        "order_number": o.order_number,
        "customer": o.customer,
        "total": float(o.total) if o.total is not None else 0.0,
        "status": o.status,
    }

@orders_bp.get("/")
def list_orders():
    q = Order.query.order_by(Order.id.desc())
    items = [_serialize(o) for o in q.limit(200).all()]
    return jsonify({"items": items, "total": q.count()})

@orders_bp.post("/")
def create_order():
    data = request.get_json(silent=True) or {}
    order_number = (data.get("order_number") or "").strip()
    customer = (data.get("customer") or "").strip()
    total = data.get("total", 0)
    status = (data.get("status") or "pending").strip() or "pending"

    if not order_number or not customer:
        return jsonify({"error": "Campos obrigatórios: order_number, customer"}), 400

    try:
        total = Decimal(str(total or 0))
    except (InvalidOperation, ValueError):
        return jsonify({"error": "Total inválido"}), 400

    o = Order(order_number=order_number, customer=customer, total=total, status=status)
    db.session.add(o)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "order_number já existe"}), 409

    return jsonify(_serialize(o) | {"id": o.id}), 201

@orders_bp.get("/<int:order_id>")
def get_order(order_id: int):
    o = Order.query.get_or_404(order_id)
    return jsonify(_serialize(o))

@orders_bp.put("/<int:order_id>")
def update_order(order_id: int):
    o = Order.query.get_or_404(order_id)
    data = request.get_json(silent=True) or {}

    if "order_number" in data:
        o.order_number = (data["order_number"] or "").strip()
    if "customer" in data:
        o.customer = (data["customer"] or "").strip()
    if "total" in data:
        try:
            o.total = Decimal(str(data["total"] or 0))
        except (InvalidOperation, ValueError):
            return jsonify({"error": "Total inválido"}), 400
    if "status" in data:
        o.status = (data["status"] or "").strip() or o.status

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "order_number já existe"}), 409

    return jsonify(_serialize(o))

@orders_bp.delete("/<int:order_id>")
def delete_order(order_id: int):
    o = Order.query.get_or_404(order_id)
    db.session.delete(o)
    db.session.commit()
    return jsonify({"deleted": order_id})
