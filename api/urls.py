from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ProductViewSet, health

router = DefaultRouter()
router.register(r"products", ProductViewSet, basename="products")

urlpatterns = [
    path("health", health, name="health"),
    path("", include(router.urls)),
]





