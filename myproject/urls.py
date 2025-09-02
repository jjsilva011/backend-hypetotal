# myproject/urls.py
from django.contrib import admin
from django.urls import path, include

from api.views import seed_products  # se quiser expor a doc do OPTIONS em /api/seed/ também

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("api.urls")),
]




