# api/urls.py — router + health + PIX/Card endpoints
from . import customer_views as cust_views
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from django.http import JsonResponse

from .views import (
    ProductViewSet,
    SupplierViewSet,
    OrderViewSet,
    CategoryViewSet,
)

from . import payments as pay_views

def health(request):
    return JsonResponse({"service": "Hype Total Backend", "status": "healthy"})

router = DefaultRouter()
router.register(r"products", ProductViewSet, basename="product")
router.register(r"suppliers", SupplierViewSet, basename="supplier")
router.register(r"orders", OrderViewSet, basename="order")
router.register(r"categories", CategoryViewSet, basename="category")

urlpatterns = [
    # Health com e sem barra
    path("health", health),
    path("health/", health),

    # Carrinho
    path("cart/",            pay_views.cart_detail, name="cart-detail"),
    path("cart/add/",        pay_views.cart_add,    name="cart-add"),
    path("cart/update/",     pay_views.cart_update, name="cart-update"),
    path("cart/clear/",      pay_views.cart_clear,  name="cart-clear"),

    # Clientes (cadastro + verificação)
    path("customers/register/",      cust_views.register_customer, name="customer-register"),
    path("customers/verify-email/",  cust_views.verify_email,      name="customer-verify-email"),
    path("customers/verify-phone/",  cust_views.verify_phone,      name="customer-verify-phone"),
    path("customers/<int:pk>/",      cust_views.customer_detail,   name="customer-detail"),

    # Pagamentos — PIX e MP
    path("checkout/pix/",            pay_views.checkout_pix,        name="checkout-pix"),
    path("payments/mp/webhook/",     pay_views.mp_webhook,          name="mp-webhook"),
    path("payments/mp/public_key/",  pay_views.mp_public_key,       name="mp-public-key"),
    path("payments/mp/card/",        pay_views.mp_card_pay,         name="mp-card-pay"),
    path("payments/mp/issuers/",     pay_views.mp_card_issuers,     name="mp-card-issuers"),
    path("payments/mp/installments/",pay_views.mp_installments,     name="mp-installments"),

    # ViewSets
    path("", include(router.urls)),
]
