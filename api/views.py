# api/views.py — Category com annotate(product_count) + Products filtros + Orders read/write

from django.db.models import Count
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

from .models import Product, Supplier, Order, Category
from .serializers import (
    ProductSerializer,
    SupplierSerializer,
    OrderReadSerializer,
    OrderCreateSerializer,
    CategorySerializer,
)

# -------------------------
# Categorias (read-only)
# -------------------------
class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [AllowAny]
    serializer_class = CategorySerializer

    def get_queryset(self):
        rel = "products"
        try:
            Category._meta.get_field("products")  # type: ignore[attr-defined]
        except Exception:
            rel = "product_set"
        return Category.objects.all().annotate(product_count=Count(rel)).order_by("name")

# -------------------------
# Produtos (CRUD)
# -------------------------
class ProductViewSet(viewsets.ModelViewSet):
    permission_classes = [AllowAny]
    serializer_class = ProductSerializer
    queryset = Product.objects.all().select_related("category").order_by("-id")

    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "sku", "description"]
    ordering_fields = ["id", "name", "price_cents", "stock", "created_at"]

    def get_queryset(self):
        qs = super().get_queryset()
        qp = self.request.query_params
        category_id  = qp.get("category_id")
        category     = qp.get("category")
        category_slug= qp.get("category_slug")
        if category_id or category:
            qs = qs.filter(category_id=category_id or category)
        if category_slug:
            qs = qs.filter(category__slug=category_slug)
        return qs

    @action(detail=False, methods=["post"])
    def seed(self, request):
        from django.conf import settings
        if not (getattr(settings, "ENABLE_SEED", False) or settings.DEBUG):
            return Response({"detail": "Seed desabilitado."}, status=403)
        import random, string
        created = 0
        for _ in range(12):
            sku = "SKU-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
            Product.objects.create(
                name=f"Produto {sku}",
                sku=sku,
                description="",
                price_cents=random.choice([5990, 9900, 12990, 19990, 29990]),
                stock=random.randint(0, 50),
                image_url=f"https://picsum.photos/seed/{sku}/600/600",
            )
            created += 1
        return Response({"created": created})

# -------------------------
# Fornecedores (CRUD)
# -------------------------
class SupplierViewSet(viewsets.ModelViewSet):
    permission_classes = [AllowAny]
    serializer_class = SupplierSerializer
    queryset = Supplier.objects.all().order_by("name")
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "email", "contact_person", "phone"]
    ordering_fields = ["name", "created_at", "updated_at"]

# -------------------------
# Pedidos (CRUD) — leitura e escrita separadas
# -------------------------
class OrderViewSet(viewsets.ModelViewSet):
    permission_classes = [AllowAny]
    queryset = Order.objects.all().prefetch_related("items__product").order_by("-created_at")
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ["created_at", "total_price_cents", "status"]

    def get_serializer_class(self):
        if self.request.method in ("GET",):
            return OrderReadSerializer
        return OrderCreateSerializer

    def list(self, request, *args, **kwargs):
        qs = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(qs)
        serializer = OrderReadSerializer(page or qs, many=True, context={"request": request})
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        obj = self.get_object()
        data = OrderReadSerializer(obj, context={"request": request}).data
        return Response(data)

    def create(self, request, *args, **kwargs):
        serializer = OrderCreateSerializer(data=request.data, context={"request": request})
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        try:
            order = serializer.save()
        except Exception as e:
            return Response({"detail": f"Falha ao criar pedido: {e}"}, status=400)
        read = OrderReadSerializer(order, context={"request": request})
        return Response(read.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        return Response({"detail": "Atualização direta de pedidos não suportada."}, status=405)

    def partial_update(self, request, *args, **kwargs):
        return Response({"detail": "Atualização direta de pedidos não suportada."}, status=405)

    def destroy(self, request, *args, **kwargs):
        obj = self.get_object()
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)





