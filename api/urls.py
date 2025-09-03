from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import health, ProductViewSet, SeedView

router = DefaultRouter()
router.register(r'products', ProductViewSet, basename='product')

urlpatterns = [
    # health (sem e com / para evitar 404 do health-check)
    path('health', health, name='health_no_slash'),
    path('health/', health, name='health'),

    # seed antes do router para não conflitar com /products/{id}/
    path('products/seed/', SeedView.as_view(), name='products-seed'),

    # endpoints REST do DRF:
    path('', include(router.urls)),
]







