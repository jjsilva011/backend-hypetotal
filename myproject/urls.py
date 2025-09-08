

# myproject/urls.py — API + Admin + MEDIA (dev)
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("api.urls")),  # /api/health, /api/products/, /api/categories/ etc.
]

# Servir uploads locais em dev (DEBUG=True)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)






