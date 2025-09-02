import random
import string
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .models import Product
from .serializers import ProductSerializer


@api_view(["GET"])
@permission_classes([AllowAny])
def health(_request):
    return Response({"service": "Hype Total Backend", "status": "healthy"})


class ProductViewSet(viewsets.ModelViewSet):
    """
    /api/products/    -> GET (lista), POST (cria)
    /api/products/{id}/ -> GET/PUT/PATCH/DELETE
    /api/products/seed/ -> POST (gera N produtos demo)
    """
    permission_classes = [AllowAny]
    queryset = Product.objects.all()
    serializer_class = ProductSerializer

    def list(self, request, *args, **kwargs):
        # paginação simples por query params page/per_page (compatível com DRF PageNumberPagination)
        return super().list(request, *args, **kwargs)

    @action(detail=False, methods=["post"], url_path="seed")
    def seed(self, request):
        try:
            n = int(request.query_params.get("n", "12"))
        except ValueError:
            n = 12
        n = max(1, min(n, 100))

        created = 0
        for _ in range(n):
            sku = "SKU-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
            price_cents = random.randint(1000, 100000)
            stock = random.randint(0, 100)
            Product.objects.create(
                name=f"Produto {sku}",
                sku=sku,
                description="Produto de demonstração para catálogo.",
                price_cents=price_cents,
                stock=stock,
            )
            created += 1

        return Response({"created": created}, status=status.HTTP_201_CREATED)




