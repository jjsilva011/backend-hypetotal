from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ProductViewSet
from rest_framework.response import Response
from rest_framework.decorators import api_view

router = DefaultRouter()
router.register("products", ProductViewSet, basename="products")

@api_view(["GET"])
def health(_request):
    return Response({"service": "Hype Total Backend", "status": "healthy"})

@api_view(["GET"])
def status(_request):
    return Response({"ok": True, "status": "healthy", "service": "Hype Total Backend"})

urlpatterns = [
    path("", include(router.urls)),
    path("health", health),
    path("status", status),
]



