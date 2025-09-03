# api/views.py
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

# --- Importações atualizadas ---
from .models import Product, Supplier, Order
from .serializers import ProductSerializer, SupplierSerializer, OrderSerializer


# ------------------------------------------------------------
# Health check
# ------------------------------------------------------------
def health(request ):
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
# ------------------------------------------------------------
class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all().order_by("-id")
    serializer_class = ProductSerializer
    permission_classes = [AllowAny]
    pagination_class = StandardResultsSetPagination


# ------------------------------------------------------------
# Suppliers CRUD
# ------------------------------------------------------------
class SupplierViewSet(viewsets.ModelViewSet):
    queryset = Supplier.objects.all().order_by("name")
    serializer_class = SupplierSerializer
    permission_classes = [AllowAny]
    pagination_class = StandardResultsSetPagination


# --- ADICIONE A VIEWSET DE ORDER ABAIXO ---
# ------------------------------------------------------------
# Orders CRUD
# ------------------------------------------------------------
class OrderViewSet(viewsets.ModelViewSet):
    # Usamos .prefetch_related('items__product') para otimizar a consulta,
    # buscando todos os itens e seus produtos relacionados de uma só vez.
    queryset = Order.objects.all().prefetch_related('items__product').order_by("-created_at")
    serializer_class = OrderSerializer
    permission_classes = [AllowAny]
    pagination_class = StandardResultsSetPagination


# ------------------------------------------------------------
# Seed de produtos de demonstração
# ------------------------------------------------------------
class SeedView(generics.GenericAPIView):
    serializer_class = ProductSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs) -> Response:
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

        n = max(1, min(n, 100))

        created = 0
        with transaction.atomic():
            for _ in range(n):
                sku = self._random_sku()
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











