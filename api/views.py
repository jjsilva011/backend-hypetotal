# C:\Users\jails\OneDrive\Desktop\Backend HypeTotal\api\views.py
import random, string
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Product
from .serializers import ProductSerializer
from django.utils import timezone

class ProductViewSet(viewsets.ViewSet):
    # GET /api/products/
    def list(self, request):
        qs = Product.objects.order_by("-id")
        data = ProductSerializer(qs, many=True).data
        return Response({"count": qs.count(), "results": data})

    # GET /api/products/seed/?n=12
    @action(detail=False, methods=["get"])
    def seed(self, request):
        n = int(request.query_params.get("n", 10))
        ids = []
        for _ in range(n):
            sku = "SKU-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
            p = Product.objects.create(
                name=f"Produto {sku}",
                sku=sku,
                price_cents=random.randint(1_000, 99_999),
                created_at=timezone.now(),
            )
            ids.append(p.id)
        return Response({"created": n, "ids": ids})

