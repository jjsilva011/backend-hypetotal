from __future__ import annotations

import os
import random
import string
from typing import List

from django.conf import settings
from django.db import IntegrityError, transaction
from django.http import JsonResponse
from django.utils import timezone

from rest_framework import generics, status, viewsets
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination

from .models import Product
from .serializers import ProductSerializer


# ------------------------------------------------------------
# Health check
# ------------------------------------------------------------
def health(request):
    """
    GET /api/health  -> 200 {"service": "...", "status": "healthy"}
    (Também é mapeado em /api/health/ no urls.py)
    """
    return JsonResponse({"service": "Hype Total Backend", "status": "healthy"})


# ------------------------------------------------------------
# Paginação padrão (?page=1&per_page=20)
# ------------------------------------------------------------
class StandardResultsSetPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "per_page"
    max_page_size = 100


# ------------------------------------------------------------
# Products CRUD
#   /api/products/        -> GET (lista paginada), POST (cria)
#   /api/products/{id}/   -> GET/PUT/PATCH/DELETE
# ------------------------------------------------------------
class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all().order_by("-id")
    serializer_class = ProductSerializer
    permission_classes = [AllowAny]
    pagination_class = StandardResultsSetPagination


# ------------------------------------------------------------
# Seed de produtos de demonstração
#   POST /api/products/seed/?n=12
#   Requer DEBUG=True ou ENABLE_SEED=true no ambiente
#   OPTIONS deste endpoint expõe o schema ("actions") de POST
# ------------------------------------------------------------
class SeedView(generics.GenericAPIView):
    """
    Gera N produtos demo com SKU único, price_cents e stock aleatórios.
    Respeita ?n= (1..100). Resposta: 201 {"created": N}
    """
    serializer_class = ProductSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs) -> Response:
        # Segurança: só habilita em DEV ou quando explicitamente permitido
        enabled = bool(settings.DEBUG) or os.environ.get("ENABLE_SEED", "").lower() == "true"
        if not enabled:
            return Response(
                {"detail": "Seeding desabilitado. Defina ENABLE_SEED=true ou DEBUG=True."},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            n = int(request.query_params.get("n", 12))
        except ValueError:
            n = 12

        n = max(1, min(n, 100))  # clamp 1..100

        created = 0
        with transaction.atomic():
            for _ in range(n):
                sku = self._random_sku()
                # tenta algumas vezes garantir SKU único
                for _attempt in range(5):
                    try:
                        Product.objects.create(
                            name=f"Produto {sku}",
                            sku=sku,
                            description="Produto de demonstração para catálogo.",
                            price_cents=random.randint(1_000, 99_999),
                            stock=random.randint(0, 99),
                            created_at=timezone.now(),
                        )
                        created += 1
                        break
                    except IntegrityError:
                        sku = self._random_sku()

        return Response({"created": created}, status=status.HTTP_201_CREATED)

    @staticmethod
    def _random_sku(length: int = 8) -> str:
        chars = string.ascii_uppercase + string.digits
        return "SKU-" + "".join(random.choices(chars, k=length))









