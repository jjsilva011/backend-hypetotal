# api/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import ProductViewSet, seed_products

router = DefaultRouter()
router.register(r"products", ProductViewSet, basename="product")

urlpatterns = [
    path("", include(router.urls)),
    path("products/seed/", seed_products, name="products-seed"),
]





