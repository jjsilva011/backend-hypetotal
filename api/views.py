# api/views.py
import random
import string

from django.conf import settings
from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from .models import Product
from .serializers import ProductSerializer


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "per_page"
    max_page_size = 100


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all().order_by("-id")
    serializer_class = ProductSerializer
    pagination_class = StandardResultsSetPagination
    # IMPORTANTE: não sobrescreva .list(); deixe o DRF paginar.


@api_view(["POST"])
@permission_classes([AllowAny])  # ajuste conforme necessidade
def seed_products(request):
    """POST /api/products/seed/?n=12 -> cria N produtos demo.
       Em prod, só habilita se ENABLE_SEED=true ou DEBUG=True."""
    if not getattr(settings, "ENABLE_SEED", False) and not settings.DEBUG:
        return Response(status=status.HTTP_404_NOT_FOUND)

    try:
        n = int(request.GET.get("n", 10))
    except ValueError:
        n = 10

    items = []
    for _ in range(n):
        sku = "SKU-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
        items.append(Product(
            name=f"Produto {sku}",
            sku=sku,
            description="Produto de demonstração para catálogo.",
            price_cents=random.randint(1000, 100000),
            stock=random.randint(0, 100),
        ))
    Product.objects.bulk_create(items)
    return Response({"created": len(items)}, status=status.HTTP_201_CREATED)








