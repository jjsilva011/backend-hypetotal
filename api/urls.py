# api/urls.py — router + health + PIX/Card endpoints (robusto a falhas de import)
from django.urls import path, include
from django.http import JsonResponse
from rest_framework.routers import DefaultRouter

# ---- Health simples
def health(_request):
    return JsonResponse({"service": "Hype Total Backend", "status": "healthy"})

# ---- Importações defensivas (se algo falhar, não derruba o módulo)
pay_views_err = None
cust_views_err = None
views_err = None

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
    # ViewSets principais
    from .views import ProductViewSet, SupplierViewSet, OrderViewSet, CategoryViewSet
except Exception as e:
    ProductViewSet = SupplierViewSet = OrderViewSet = CategoryViewSet = None
    views_err = e

# ---- Router
router = DefaultRouter()
if ProductViewSet:
    router.register(r"products", ProductViewSet, basename="product")
if SupplierViewSet:
    router.register(r"suppliers", SupplierViewSet, basename="supplier")
if OrderViewSet:
    router.register(r"orders", OrderViewSet, basename="order")
if CategoryViewSet:
    # 🔒 garante categories/ no root
    router.register(r"categories", CategoryViewSet, basename="category")

# ---- Stubs quando módulos auxiliares não carregarem
def _stub(detail):
    return lambda _req, *a, **k: JsonResponse({"detail": detail}, status=503)

# Carrinho
cart_detail      = (pay_views.cart_detail      if pay_views and hasattr(pay_views, "cart_detail")      else _stub(f"payments indisponível: {pay_views_err}"))
cart_add         = (pay_views.cart_add         if pay_views and hasattr(pay_views, "cart_add")         else _stub(f"payments indisponível: {pay_views_err}"))
cart_update      = (pay_views.cart_update      if pay_views and hasattr(pay_views, "cart_update")      else _stub(f"payments indisponível: {pay_views_err}"))
cart_clear       = (pay_views.cart_clear       if pay_views and hasattr(pay_views, "cart_clear")       else _stub(f"payments indisponível: {pay_views_err}"))

# Pagamentos MP
checkout_pix     = (pay_views.checkout_pix     if pay_views and hasattr(pay_views, "checkout_pix")     else _stub(f"payments indisponível: {pay_views_err}"))
mp_webhook       = (pay_views.mp_webhook       if pay_views and hasattr(pay_views, "mp_webhook")       else _stub(f"payments indisponível: {pay_views_err}"))
mp_public_key    = (pay_views.mp_public_key    if pay_views and hasattr(pay_views, "mp_public_key")    else _stub(f"payments indisponível: {pay_views_err}"))
mp_card_pay      = (pay_views.mp_card_pay      if pay_views and hasattr(pay_views, "mp_card_pay")      else _stub(f"payments indisponível: {pay_views_err}"))
mp_card_issuers  = (pay_views.mp_card_issuers  if pay_views and hasattr(pay_views, "mp_card_issuers")  else _stub(f"payments indisponível: {pay_views_err}"))
mp_installments  = (pay_views.mp_installments  if pay_views and hasattr(pay_views, "mp_installments")  else _stub(f"payments indisponível: {pay_views_err}"))

# Clientes
register_customer = (cust_views.register_customer if cust_views and hasattr(cust_views, "register_customer") else _stub(f"customer_views indisponível: {cust_views_err}"))
verify_email      = (cust_views.verify_email      if cust_views and hasattr(cust_views, "verify_email")      else _stub(f"customer_views indisponível: {cust_views_err}"))
verify_phone      = (cust_views.verify_phone      if cust_views and hasattr(cust_views, "verify_phone")      else _stub(f"customer_views indisponível: {cust_views_err}"))
customer_detail   = (cust_views.customer_detail   if cust_views and hasattr(cust_views, "customer_detail")   else _stub(f"customer_views indisponível: {cust_views_err}"))

# ---- URL patterns
urlpatterns = [
    path("health", health),
    path("health/", health),

    # Carrinho
    path("cart/",            cart_detail,     name="cart-detail"),
    path("cart/add/",        cart_add,        name="cart-add"),
    path("cart/update/",     cart_update,     name="cart-update"),
    path("cart/clear/",      cart_clear,      name="cart-clear"),

    # Clientes (cadastro + verificação)
    path("customers/register/",     register_customer, name="customer-register"),
    path("customers/verify-email/", verify_email,      name="customer-verify-email"),
    path("customers/verify-phone/", verify_phone,      name="customer-verify-phone"),
    path("customers/<int:pk>/",     customer_detail,   name="customer-detail"),

    # Mercado Pago — PIX & Cartão
    path("checkout/pix/",            checkout_pix,      name="checkout-pix"),
    path("payments/mp/webhook/",     mp_webhook,        name="mp-webhook"),
    path("payments/mp/public_key/",  mp_public_key,     name="mp-public-key"),

    path("payments/mp/card/",         mp_card_pay,      name="mp-card-pay"),
    path("payments/mp/issuers/",      mp_card_issuers,  name="mp-card-issuers"),
    path("payments/mp/installments/", mp_installments,  name="mp-installments"),

    # Router (products/suppliers/orders/categories)
    path("", include(router.urls)),
]

