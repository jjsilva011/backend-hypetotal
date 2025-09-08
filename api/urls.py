# api/urls.py — robusto: ping, categories fallback, cart & MP tolerantes, orders.safe

from django.urls import path, include
from django.http import JsonResponse, HttpRequest
from rest_framework.routers import DefaultRouter

def health(_request):
    return JsonResponse({"service": "Hype Total Backend", "status": "healthy"})

# Um ping para confirmar que ESTE arquivo está ativo no container
def urls_ping(_request):
    return JsonResponse({"ok": True, "source": "api.urls.py (robusto)"})


# ----------------- imports defensivos -----------------
pay_views_err = None
cust_views_err = None
views_err = None
models_err = None
serializers_err = None

try:
    from . import payments as pay_views
except Exception as e:
    pay_views = None
    pay_views_err = e

try:
    from . import customer_views as cust_views
except Exception as e:
    cust_views = None
    cust_views_err = e

try:
    from .views import ProductViewSet, SupplierViewSet, OrderViewSet, CategoryViewSet
except Exception as e:
    ProductViewSet = SupplierViewSet = OrderViewSet = CategoryViewSet = None
    views_err = e

# Fallbacks que não dependem do DRF Router
try:
    from django.db.models import Count
    from .models import Category, Order, OrderItem, Product
except Exception as e:
    Category = Order = OrderItem = Product = None
    models_err = e

try:
    # só usamos no fallback categories se estiver disponível
    from .serializers import CategorySerializer
except Exception as e:
    CategorySerializer = None
    serializers_err = e


# ----------------- DRF Router (quando der) -----------------
router = DefaultRouter()
if ProductViewSet:
    router.register(r"products", ProductViewSet, basename="product")
if SupplierViewSet:
    router.register(r"suppliers", SupplierViewSet, basename="supplier")
if OrderViewSet:
    router.register(r"orders", OrderViewSet, basename="order")
if CategoryViewSet:
    router.register(r"categories", CategoryViewSet, basename="category")


# ----------------- helpers -----------------
def _stub(detail):
    return lambda _req, *a, **k: JsonResponse({"detail": str(detail)}, status=503)


# ----------------- Carrinho (usa payments se disponível) -----------------
cart_detail      = (pay_views.cart_detail      if pay_views and hasattr(pay_views, "cart_detail")      else _stub(f"payments indisponível: {pay_views_err}"))
cart_add         = (pay_views.cart_add         if pay_views and hasattr(pay_views, "cart_add")         else _stub(f"payments indisponível: {pay_views_err}"))
cart_update      = (pay_views.cart_update      if pay_views and hasattr(pay_views, "cart_update")      else _stub(f"payments indisponível: {pay_views_err}"))
cart_clear       = (pay_views.cart_clear       if pay_views and hasattr(pay_views, "cart_clear")       else _stub(f"payments indisponível: {pay_views_err}"))

checkout_pix     = (pay_views.checkout_pix     if pay_views and hasattr(pay_views, "checkout_pix")     else _stub(f"payments indisponível: {pay_views_err}"))
mp_webhook       = (pay_views.mp_webhook       if pay_views and hasattr(pay_views, "mp_webhook")       else _stub(f"payments indisponível: {pay_views_err}"))
mp_public_key    = (pay_views.mp_public_key    if pay_views and hasattr(pay_views, "mp_public_key")    else _stub(f"payments indisponível: {pay_views_err}"))
mp_card_pay      = (pay_views.mp_card_pay      if pay_views and hasattr(pay_views, "mp_card_pay")      else _stub(f"payments indisponível: {pay_views_err}"))
mp_card_issuers  = (pay_views.mp_card_issuers  if pay_views and hasattr(pay_views, "mp_card_issuers")  else _stub(f"payments indisponível: {pay_views_err}"))
mp_installments  = (pay_views.mp_installments  if pay_views and hasattr(pay_views, "mp_installments")  else _stub(f"payments indisponível: {pay_views_err}"))


# ----------------- Fallbacks prontos para produção -----------------
def categories_list_fallback(_request: HttpRequest):
    """
    /api/categories/ — funciona mesmo se o router não registrou.
    Retorna: [{id,name,slug,product_count}]
    """
    if not Category:
        return JsonResponse({"detail": f"models indisponível: {models_err}"}, status=503)
    rel = "products"
    try:
        # se o related_name não existir, usa product_set
        Category._meta.get_field("products")  # type: ignore
    except Exception:
        rel = "product_set"
    qs = Category.objects.all().annotate(product_count=Count(rel)).order_by("name")
    if CategorySerializer:
        data = CategorySerializer(qs, many=True).data
        return JsonResponse(data, safe=False)
    # serialização manual, se serializer não carregar
    data = [{"id": c.id, "name": c.name, "slug": c.slug, "product_count": getattr(c, "product_count", 0)} for c in qs]
    return JsonResponse(data, safe=False)


def orders_list_safe(_request: HttpRequest):
    """
    /api/orders.safe/ — lista segura (sem serializers encadeados) para eliminar 500.
    Inclui itens com product_id, quantity, price_cents.
    """
    if not Order:
        return JsonResponse({"detail": f"models indisponível: {models_err}"}, status=503)
    out = []
    qs = Order.objects.all().order_by("-created_at")[:200]
    # Pré-busca itens para evitar N queries
    items_by_order = {}
    if OrderItem:
        for it in OrderItem.objects.filter(order_id__in=[o.id for o in qs]):
            items_by_order.setdefault(it.order_id, []).append({
                "product_id": getattr(it, "product_id", None),
                "quantity": int(getattr(it, "quantity", 0) or 0),
                "price_cents": int(getattr(it, "price_cents", 0) or 0),
            })
    for o in qs:
        out.append({
            "id": o.id,
            "customer_name": o.customer_name,
            "status": o.status,
            "total_price_cents": int(getattr(o, "total_price_cents", 0) or 0),
            "created_at": o.created_at,
            "items": items_by_order.get(o.id, []),
        })
    return JsonResponse(out, safe=False)


def orders_create_safe(request: HttpRequest):
    """
    /api/orders.safe/ (POST) — cria pedido de forma robusta.
    Body: { "customer_name": "...", "items": [ { "product_id": 31, "quantity": 1 }, ... ] }
    """
    if request.method != "POST":
        return JsonResponse({"detail": "Method not allowed"}, status=405)
    if not (Order and OrderItem and Product):
        return JsonResponse({"detail": f"models indisponível: {models_err}"}, status=503)

    data = getattr(request, "data", None) or {}
    name = (data.get("customer_name") or "").strip() or "Cliente"
    raw_items = data.get("items") or []
    if not isinstance(raw_items, list) or not raw_items:
        return JsonResponse({"detail": "items obrigatórios."}, status=400)

    # normalizar itens
    items = []
    for it in raw_items:
        try:
            pid = int(it.get("product_id"))
            qty = int(it.get("quantity") or 0)
        except Exception:
            continue
        if qty <= 0:
            continue
        p = Product.objects.filter(pk=pid).first()
        if not p:
            return JsonResponse({"detail": f"Produto {pid} não encontrado."}, status=400)
        items.append((p, qty, int(p.price_cents or 0)))
    if not items:
        return JsonResponse({"detail": "Nenhum item válido."}, status=400)

    # cria pedido + itens
    from django.db import transaction
    with transaction.atomic():
        o = Order.objects.create(customer_name=name, status="pending", total_price_cents=0)
        total = 0
        for p, qty, price in items:
            OrderItem.objects.create(order=o, product=p, quantity=qty, price_cents=price)
            total += qty * price
        o.total_price_cents = total
        o.save(update_fields=["total_price_cents"])

    return JsonResponse({
        "id": o.id,
        "customer_name": o.customer_name,
        "status": o.status,
        "total_price_cents": o.total_price_cents,
        "created_at": o.created_at,
        "items": [{"product_id": p.id, "quantity": qty, "price_cents": price} for p, qty, price in items],
    }, status=201)


# ----------------- URL patterns -----------------
urlpatterns = [
    path("health", health),
    path("health/", health),

    # ping para provar que ESTE arquivo está ativo
    path("urls-ping/", urls_ping),

    # Fallback categories SEM depender do router
    path("categories/", categories_list_fallback, name="categories-fallback"),

    # Carrinho
    path("cart/",            cart_detail,     name="cart-detail"),
    path("cart/add/",        cart_add,        name="cart-add"),
    path("cart/update/",     cart_update,     name="cart-update"),
    path("cart/clear/",      cart_clear,      name="cart-clear"),

    # Clientes
    path("customers/register/",     (cust_views.register_customer if cust_views else _stub(f"customer_views: {cust_views_err}")), name="customer-register"),
    path("customers/verify-email/", (cust_views.verify_email      if cust_views else _stub(f"customer_views: {cust_views_err}")), name="customer-verify-email"),
    path("customers/verify-phone/", (cust_views.verify_phone      if cust_views else _stub(f"customer_views: {cust_views_err}")), name="customer-verify-phone"),
    path("customers/<int:pk>/",     (cust_views.customer_detail   if cust_views else _stub(f"customer_views: {cust_views_err}")), name="customer-detail"),

    # Mercado Pago
    path("checkout/pix/",            checkout_pix,      name="checkout-pix"),
    path("payments/mp/webhook/",     mp_webhook,        name="mp-webhook"),
    path("payments/mp/public_key/",  mp_public_key,     name="mp-public-key"),
    path("payments/mp/card/",        mp_card_pay,       name="mp-card-pay"),
    path("payments/mp/issuers/",     mp_card_issuers,   name="mp-card-issuers"),
    path("payments/mp/installments/",mp_installments,   name="mp-installments"),

    # Lista/Criação segura de pedidos (não conflita com /orders/ do router)
    path("orders.safe/", orders_list_safe, name="orders-list-safe"),
    path("orders.safe/create", orders_create_safe, name="orders-create-safe"),

    # Router por último (se CategoryViewSet carregar, /categories/ do router também existirá)
    path("", include(router.urls)),
]



