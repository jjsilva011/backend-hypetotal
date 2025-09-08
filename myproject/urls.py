# myproject/urls.py — força rotas críticas antes do include('api.urls')
from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse

# Imports defensivos
pay_err = None
views_err = None

try:
    from api import payments as pay_views
except Exception as e:
    pay_views = None
    pay_err = e

try:
    from api import views as api_views  # aqui estão os fallbacks abaixo
except Exception as e:
    api_views = None
    views_err = e


def _stub(detail):
    return lambda _req, *a, **k: JsonResponse({"detail": str(detail)}, status=503)


def urls_ping(_request):
    return JsonResponse({"ok": True, "source": "myproject.urls (robusto)"})


def health(_request):
    return JsonResponse({"service": "Hype Total Backend", "status": "healthy"})


# Mapeia handlers (se import falhar, responde 503 explicando)
categories_list_fallback = (
    api_views.categories_list_fallback
    if api_views and hasattr(api_views, "categories_list_fallback")
    else _stub(f"api.views indisponível: {views_err}")
)

orders_list_safe = (
    api_views.orders_list_safe
    if api_views and hasattr(api_views, "orders_list_safe")
    else _stub(f"api.views indisponível: {views_err}")
)

orders_create_safe = (
    api_views.orders_create_safe
    if api_views and hasattr(api_views, "orders_create_safe")
    else _stub(f"api.views indisponível: {views_err}")
)

cart_detail = (
    pay_views.cart_detail
    if pay_views and hasattr(pay_views, "cart_detail")
    else _stub(f"payments indisponível: {pay_err}")
)

cart_add = (
    pay_views.cart_add
    if pay_views and hasattr(pay_views, "cart_add")
    else _stub(f"payments indisponível: {pay_err}")
)

cart_update = (
    pay_views.cart_update
    if pay_views and hasattr(pay_views, "cart_update")
    else _stub(f"payments indisponível: {pay_err}")
)

cart_clear = (
    pay_views.cart_clear
    if pay_views and hasattr(pay_views, "cart_clear")
    else _stub(f"payments indisponível: {pay_err}")
)

mp_public_key = (
    pay_views.mp_public_key
    if pay_views and hasattr(pay_views, "mp_public_key")
    else _stub(f"payments indisponível: {pay_err}")
)


urlpatterns = [
    path("admin/", admin.site.urls),

    # health e ping — garantidos
    path("api/health", health),
    path("api/health/", health),
    path("api/urls-ping/", urls_ping),

    # categorias (fallback que não depende do router)
    path("api/categories/", categories_list_fallback, name="categories-fallback"),

    # carrinho
    path("api/cart/",        cart_detail,  name="cart-detail"),
    path("api/cart/add/",    cart_add,     name="cart-add"),
    path("api/cart/update/", cart_update,  name="cart-update"),
    path("api/cart/clear/",  cart_clear,   name="cart-clear"),

    # orders SAFE (lista e criação robustas)
    path("api/orders.safe/",         orders_list_safe,   name="orders-list-safe"),
    path("api/orders.safe/create",   orders_create_safe, name="orders-create-safe"),

    # MP public key (útil pro front)
    path("api/payments/mp/public_key/", mp_public_key, name="mp-public-key"),

    # por último, tudo que o app api já expõe (products/suppliers/orders/…)
    path("api/", include("api.urls")),
]







