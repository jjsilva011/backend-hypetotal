# api/payments.py — Carrinho + PIX + Cartão (MP v2), issuers/parcelas, webhook e public_key (robustos)
from __future__ import annotations

import os
import re
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List, Tuple

from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, HttpRequest
from django.db import transaction
from django.shortcuts import get_object_or_404

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny

from .models import Product, Order, OrderItem

# --- Mercado Pago SDK (opcional) ---
try:
    import mercadopago
except Exception:
    mercadopago = None

MP_ACCESS_TOKEN = os.getenv("MP_ACCESS_TOKEN", "")
MP_PUBLIC_KEY = os.getenv("MP_PUBLIC_KEY", "")
MP_TEST_MODE = os.getenv("MP_WEBHOOK_TEST_MODE", "0") == "1"


# ======================================================================
# Utils
# ======================================================================
def _sdk():
    if mercadopago is None:
        raise RuntimeError("Mercado Pago SDK indisponível.")
    if not MP_ACCESS_TOKEN:
        raise RuntimeError("MP_ACCESS_TOKEN ausente no ambiente.")
    return mercadopago.SDK(MP_ACCESS_TOKEN)

def _cents_to_amount(cents: int) -> float:
    v = (Decimal(int(cents)) / Decimal(100)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return float(v)

def _only_digits(s: str) -> str:
    return re.sub(r"\D+", "", s or "")


# ======================================================================
# Carrinho (na sessão)
# ======================================================================
def _ensure_cart(request: HttpRequest) -> Dict[str, Any]:
    if "cart" not in request.session or not isinstance(request.session.get("cart"), dict):
        request.session["cart"] = {"items": []}
    return request.session["cart"]

def _prod_brief(p: Product) -> Dict[str, Any]:
    img = ""
    try:
        img = p.primary_image_url() or ""
    except Exception:
        img = p.image_url or ""
    return {
        "product_id": p.id,
        "name": p.name,
        "sku": p.sku,
        "primary_image_url": img,
        "price_cents": int(p.price_cents or 0),
    }

def _recalc_from_items(items: List[Dict[str, Any]]) -> Tuple[int, int]:
    total_items = 0
    total_cents = 0
    for it in items:
        qty = int(it.get("quantity", 0) or 0)
        price = int(it.get("price_cents", 0) or 0)
        if qty > 0 and price >= 0:
            total_items += qty
            total_cents += qty * price
    return total_items, total_cents

def _normalize_items(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for it in items or []:
        try:
            pid = int(it.get("product_id"))
            qty = max(0, int(it.get("quantity") or 0))
        except Exception:
            continue
        if qty <= 0:
            continue
        p = Product.objects.filter(pk=pid).first()
        if not p:
            continue
        price = int(it.get("price_cents") or p.price_cents or 0)
        out.append({"product_id": p.id, "quantity": qty, "price_cents": price})
    return out

def _cart_response(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    pids = [it["product_id"] for it in items]
    products = {p.id: p for p in Product.objects.filter(id__in=pids)}

    view_items: List[Dict[str, Any]] = []
    for it in items:
        p = products.get(it["product_id"])
        if not p:
            continue
        base = _prod_brief(p)
        base["quantity"] = int(it["quantity"])
        base["line_total_cents"] = base["quantity"] * int(it["price_cents"])
        base["price_cents"] = int(it.get("price_cents", base["price_cents"]))
        view_items.append(base)

    total_items, total_cents = _recalc_from_items(items)
    return {"items": view_items, "total_items": total_items, "total_cents": total_cents}


# ---------- Endpoints do carrinho ----------
@api_view(["GET"])
@permission_classes([AllowAny])
def cart_detail(request: HttpRequest):
    cart = _ensure_cart(request)
    items = _normalize_items(cart.get("items", []))
    cart["items"] = items
    request.session.modified = True
    return JsonResponse(_cart_response(items))

@api_view(["POST"])
@permission_classes([AllowAny])
def cart_add(request: HttpRequest):
    data = request.data or {}
    try:
        pid = int(data.get("product_id"))
        qty = int(data.get("quantity") or 1)
    except Exception:
        return JsonResponse({"detail": "Parâmetros inválidos."}, status=400)
    if qty <= 0:
        return JsonResponse({"detail": "Quantidade deve ser >= 1."}, status=400)

    p = Product.objects.filter(pk=pid).first()
    if not p:
        return JsonResponse({"detail": "Produto não encontrado."}, status=404)

    cart = _ensure_cart(request)
    items = _normalize_items(cart.get("items", []))

    for it in items:
        if it["product_id"] == p.id:
            it["quantity"] = int(it["quantity"]) + qty
            it["price_cents"] = int(it.get("price_cents") or p.price_cents or 0)
            break
    else:
        items.append({"product_id": p.id, "quantity": qty, "price_cents": int(p.price_cents or 0)})

    cart["items"] = items
    request.session["cart"] = cart
    request.session.modified = True
    return JsonResponse(_cart_response(items))

@api_view(["POST"])
@permission_classes([AllowAny])
def cart_update(request: HttpRequest):
    data = request.data or {}
    cart = _ensure_cart(request)
    items = _normalize_items(cart.get("items", []))

    if "items" in data and isinstance(data["items"], list):
        new_items = []
        for it in data["items"]:
            try:
                pid = int(it.get("product_id"))
                qty = int(it.get("quantity") or 0)
            except Exception:
                continue
            if qty <= 0:
                continue
            p = Product.objects.filter(pk=pid).first()
            if not p:
                continue
            new_items.append({"product_id": p.id, "quantity": qty, "price_cents": int(p.price_cents or 0)})
        items = _normalize_items(new_items)
    else:
        try:
            pid = int(data.get("product_id"))
            qty = int(data.get("quantity") or 0)
        except Exception:
            return JsonResponse({"detail": "Parâmetros inválidos."}, status=400)

        updated: List[Dict[str, Any]] = []
        for it in items:
            if it["product_id"] == pid:
                if qty > 0:
                    it["quantity"] = qty
                    it["price_cents"] = int(it.get("price_cents") or Product.objects.get(pk=pid).price_cents or 0)
                    updated.append(it)
                # qty <= 0 => remove
            else:
                updated.append(it)
        items = _normalize_items(updated)

    cart["items"] = items
    request.session["cart"] = cart
    request.session.modified = True
    return JsonResponse(_cart_response(items))

@api_view(["POST"])
@permission_classes([AllowAny])
def cart_clear(request: HttpRequest):
    request.session["cart"] = {"items": []}
    request.session.modified = True
    return JsonResponse({"items": [], "total_items": 0, "total_cents": 0})


# ======================================================================
# Snapshot do carrinho -> Order
# ======================================================================
def _cart_snapshot(request: HttpRequest) -> Tuple[List[Dict[str, Any]], int]:
    """
    Retorna (items, total_cents) a partir da sessão.
    Suporta:
      A) {"items":[{product_id, quantity, price_cents?}, ...]}
      B) {"100": 2, "101": 1}  -> dict id->qty (formato legado)
    """
    sess = request.session or {}
    raw = sess.get("cart") or sess.get("CART") or {}

    items: List[Dict[str, Any]] = []
    total_cents = 0

    try:
        # Caso A (preferido)
        if isinstance(raw, dict) and isinstance(raw.get("items"), list):
            norm = _normalize_items(raw["items"])
            for it in norm:
                line = int(it["price_cents"]) * int(it["quantity"])
                total_cents += line
                items.append({
                    "product_id": int(it["product_id"]),
                    "quantity": int(it["quantity"]),
                    "price_cents": int(it["price_cents"]),
                })
            return items, total_cents

        # Caso B (legado): dict id->qty
        if isinstance(raw, dict):
            keys_like_ids = [k for k in raw.keys() if re.match(r"^\d+$", str(k))]
            if keys_like_ids:
                pids = [int(k) for k in keys_like_ids]
                products = {p.id: p for p in Product.objects.filter(id__in=pids)}
                for k in keys_like_ids:
                    pid = int(k)
                    qty = int(raw.get(k) or 0)
                    p = products.get(pid)
                    if not p or qty <= 0:
                        continue
                    price_cents = int(p.price_cents or 0)
                    items.append({"product_id": p.id, "quantity": qty, "price_cents": price_cents})
                    total_cents += qty * price_cents
                return items, total_cents
    except Exception:
        pass

    return [], 0

@transaction.atomic
def _create_order_from_cart(request: HttpRequest, customer_name: str, customer_email: str = "") -> Tuple[Order, List[OrderItem], int]:
    """
    Cria Order + OrderItems a partir do carrinho da sessão.
    """
    items, total = _cart_snapshot(request)
    if total <= 0 or not items:
        raise ValueError("Carrinho vazio.")

    order = Order.objects.create(
        customer_name=customer_name or "Cliente",
        status="pending",
        total_price_cents=0,
    )

    order_items: List[OrderItem] = []
    for it in items:
        oi = OrderItem.objects.create(
            order=order,
            product=get_object_or_404(Product, pk=it["product_id"]),
            quantity=int(it["quantity"]),
            price_cents=int(it["price_cents"]),
        )
        order_items.append(oi)

    order.total_price_cents = sum(oi.price_cents * oi.quantity for oi in order_items)
    for field, value in [
        ("payment_provider", "mercadopago"),
        ("external_reference", str(order.id)),
    ]:
        if hasattr(order, field):
            setattr(order, field, value)
    order.save()
    return order, order_items, order.total_price_cents


# ======================================================================
# PIX
# ======================================================================
@api_view(["POST"])
@permission_classes([AllowAny])
def checkout_pix(request: HttpRequest):
    """
    POST /api/checkout/pix/
    Body: { customer: { name, email } }
    """
    customer = (request.data or {}).get("customer") or {}
    name = (customer.get("name") or "").strip() or "Cliente"
    email = (customer.get("email") or "").strip()

    try:
        order, _items, total_cents = _create_order_from_cart(request, name, email)
    except ValueError as e:
        return JsonResponse({"detail": str(e)}, status=400)

    if MP_TEST_MODE and (request.data or {}).get("test_status"):
        test_status = str(request.data.get("test_status"))
        if hasattr(order, "payment_method"):
            order.payment_method = "pix"
        if hasattr(order, "payment_reference"):
            order.payment_reference = f"TEST-PIX-{test_status.upper()}"
        if test_status == "approved":
            order.status = "paid"
        elif test_status in ("rejected", "cancelled", "canceled", "failed"):
            order.status = "failed"
        else:
            order.status = "pending"
        order.save()
        return JsonResponse({
            "ok": True,
            "test_mode": True,
            "order_id": order.id,
            "status": order.status,
            "pix": {
                "qr_code": "TEST_ONLY",
                "qr_code_base64": "",
                "copy_and_paste": f"TEST-PIX-{order.id}",
            }
        })

    try:
        sdk = _sdk()
        amount = _cents_to_amount(total_cents)
        body = {
            "transaction_amount": amount,
            "payment_method_id": "pix",
            "payer": {"email": email or "noemail+hypetotal@example.com"},
            "external_reference": str(order.id),
            "description": f"Pedido #{order.id} — HypeTotal (PIX)",
        }
        result = sdk.payment().create(body)
        resp = result.get("response") or {}
        mp_status = (resp.get("status") or "").lower()
        payment_id = resp.get("id")
        poi = (resp.get("point_of_interaction") or {}).get("transaction_data") or {}
        qr = {
            "qr_code": poi.get("qr_code", ""),
            "qr_code_base64": poi.get("qr_code_base64", ""),
            "copy_and_paste": poi.get("qr_code", ""),
        }

        if hasattr(order, "payment_method"):
            order.payment_method = "pix"
        if hasattr(order, "payment_reference") and payment_id:
            order.payment_reference = str(payment_id)
        if mp_status == "approved":
            order.status = "paid"
        elif mp_status in ("rejected", "cancelled", "canceled"):
            order.status = "failed"
        else:
            order.status = "pending"
        order.save()

        return JsonResponse({
            "ok": True,
            "order_id": order.id,
            "status": order.status,
            "pix": {"payment_id": payment_id, **qr}
        })
    except Exception as e:
        return JsonResponse({"detail": f"Falha no PIX: {e}"}, status=500)


# ======================================================================
# Cartão
# ======================================================================
@api_view(["POST"])
@permission_classes([AllowAny])
def mp_card_pay(request: HttpRequest):
    """
    POST /api/payments/mp/card/
    Body:
    {
      "customer": { "name": "...", "email": "..." },
      "card": { "token": "...", "payment_method_id": "visa"?, "issuer_id": 123?, "installments": 1, "doc_number": "..." }
    }
    """
    data = request.data or {}
    customer = data.get("customer") or {}
    name = (customer.get("name") or "").strip() or "Cliente"
    email = (customer.get("email") or "").strip()

    card = data.get("card") or {}
    token = (card.get("token") or "").strip()
    pm_id = (card.get("payment_method_id") or "").strip() or None
    issuer_id = card.get("issuer_id")  # opcional
    installments = int(card.get("installments") or 1)
    doc_number = _only_digits(card.get("doc_number") or "")

    if not token:
        return JsonResponse({"detail": "Token do cartão ausente."}, status=400)

    try:
        order, _items, total_cents = _create_order_from_cart(request, name, email)
    except ValueError as e:
        return JsonResponse({"detail": str(e)}, status=400)

    if MP_TEST_MODE and data.get("test_status"):
        t = str(data.get("test_status"))
        if hasattr(order, "payment_method"):
            order.payment_method = "card"
        if hasattr(order, "payment_reference"):
            order.payment_reference = f"TEST-CARD-{t.upper()}"
        if t == "approved":
            order.status = "paid"
        elif t in ("rejected", "cancelled", "canceled", "failed"):
            order.status = "failed"
        else:
            order.status = "pending"
        order.save()
        return JsonResponse({"ok": True, "test_mode": True, "order_id": order.id, "status": order.status})

    try:
        sdk = _sdk()
        amount = _cents_to_amount(total_cents)
        body = {
            "transaction_amount": amount,
            "token": token,
            "description": f"Pedido #{order.id} — HypeTotal (Cartão)",
            "installments": installments,
            "payer": {
                "email": email or "noemail+hypetotal@example.com",
                "identification": {"type": "CPF", "number": doc_number or "00000000000"},
            },
            "external_reference": str(order.id),
        }
        if pm_id:
            body["payment_method_id"] = pm_id
        if issuer_id:
            body["issuer_id"] = int(issuer_id)

        result = sdk.payment().create(body)
        resp = result.get("response") or {}
        mp_status = (resp.get("status") or "").lower()
        payment_id = resp.get("id")

        if hasattr(order, "payment_method"):
            order.payment_method = "card"
        if hasattr(order, "payment_reference") and payment_id:
            order.payment_reference = str(payment_id)
        if mp_status == "approved":
            order.status = "paid"
        elif mp_status in ("rejected", "cancelled", "canceled"):
            order.status = "failed"
        else:
            order.status = "pending"
        order.save()

        return JsonResponse({"ok": True, "order_id": order.id, "status": order.status, "payment_id": payment_id})
    except Exception as e:
        return JsonResponse({"detail": f"Falha no pagamento com cartão: {e}"}, status=500)


# ======================================================================
# Issuers e Parcelas
# ======================================================================
@api_view(["GET"])
@permission_classes([AllowAny])
def mp_card_issuers(request: HttpRequest):
    """
    GET /api/payments/mp/issuers/?bin=411111
    """
    bin6 = _only_digits(request.GET.get("bin", ""))[:6]
    if not bin6 or len(bin6) < 6:
        return JsonResponse({"detail": "BIN inválido."}, status=400)
    try:
        sdk = _sdk()
        res = sdk.get("/v1/payment_methods/card_issuers", params={"bin": bin6})
        return JsonResponse(res.get("response", []), safe=False)
    except Exception as e:
        return JsonResponse({"detail": f"Falha ao obter issuers: {e}"}, status=500)

@api_view(["GET"])
@permission_classes([AllowAny])
def mp_installments(request: HttpRequest):
    """
    GET /api/payments/mp/installments/?bin=411111&amount=42.44
    """
    bin6 = _only_digits(request.GET.get("bin", ""))[:6]
    amount = request.GET.get("amount")
    try:
        amount_f = float(amount)
    except Exception:
        return JsonResponse({"detail": "amount inválido."}, status=400)
    if not bin6 or len(bin6) < 6:
        return JsonResponse({"detail": "BIN inválido."}, status=400)
    try:
        sdk = _sdk()
        res = sdk.get("/v1/payment_methods/installments", params={
            "bin": bin6,
            "amount": amount_f,
            "payment_type_id": "credit_card",
        })
        return JsonResponse(res.get("response", []), safe=False)
    except Exception as e:
        return JsonResponse({"detail": f"Falha ao obter parcelas: {e}"}, status=500)


# ======================================================================
# Webhook
# ======================================================================
@csrf_exempt
@api_view(["POST"])
@permission_classes([AllowAny])
def mp_webhook(request: HttpRequest):
    """
    POST /api/payments/mp/webhook/
    Em DEV (MP_WEBHOOK_TEST_MODE=1):
      { "external_reference": "<order_id>", "test_status": "approved|rejected|cancelled" }
    """
    data = request.data or {}
    ext = str(data.get("external_reference") or "").strip()

    if MP_TEST_MODE and data.get("test_status"):
        if not ext.isdigit():
            return JsonResponse({"detail": "Order não encontrada (TEST_MODE)."}, status=404)
        order = get_object_or_404(Order, pk=int(ext))
        t = str(data.get("test_status"))
        if t == "approved":
            order.status = "paid"
        elif t in ("rejected", "cancelled", "canceled", "failed"):
            order.status = "failed"
        else:
            order.status = "pending"
        order.save()
        return JsonResponse({"ok": True, "test_mode": True})

    # Produção/sandbox real
    try:
        typ = (data.get("type") or "").lower()
        data_id = str((data.get("data") or {}).get("id") or "").strip()
        if typ != "payment" or not data_id:
            return JsonResponse({"ok": True})  # ignorado

        sdk = _sdk()
        pay = sdk.payment().get(data_id)
        presp = (pay or {}).get("response") or {}
        ext_ref = str(presp.get("external_reference") or "").strip()
        status_mp = (presp.get("status") or "").lower()
        if not ext_ref.isdigit():
            return JsonResponse({"ok": True})

        order = get_object_or_404(Order, pk=int(ext_ref))
        if status_mp == "approved":
            order.status = "paid"
        elif status_mp in ("rejected", "cancelled", "canceled"):
            order.status = "failed"
        else:
            order.status = "pending"
        if hasattr(order, "payment_reference") and presp.get("id"):
            order.payment_reference = str(presp["id"])
        order.save()
        return JsonResponse({"ok": True})
    except Exception as e:
        return JsonResponse({"detail": f"Falha no webhook: {e}"}, status=500)


# ======================================================================
# Public Key para o front
# ======================================================================
@api_view(["GET"])
@permission_classes([AllowAny])
def mp_public_key(request: HttpRequest):
    if not MP_PUBLIC_KEY:
        return JsonResponse({"public_key": "", "warning": "MP_PUBLIC_KEY ausente no backend."})
    return JsonResponse({"public_key": MP_PUBLIC_KEY})







