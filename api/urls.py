from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import health, ProductViewSet, seed

router = DefaultRouter()
router.register(r'products', ProductViewSet, basename='product')

urlpatterns = [
    # Health check (sem e com barra para evitar 301 e 404)
    path('health', health),
    path('health/', health),

    # API REST gerada pelo router
    path('', include(router.urls)),

    # Seed: POST /api/products/seed/?n=12
    path('products/seed/', seed),
]






