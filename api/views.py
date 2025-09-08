

















# api/views.py — categorias com annotate(product_count) e filtros em produtos

from django.db.models import Count
from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Product, Supplier, Order, Category
from .serializers import (
    ProductSerializer,
    SupplierSerializer,
    CategorySerializer,
    # Pedidos — serializers separados para escrita/leitura
    OrderCreateSerializer,
    OrderReadSerializer,
)


# -------------------------
# Categorias (read-only)
# -------------------------
class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CategorySerializer

    def get_queryset(self):
        # Requer que Product.category use related_name="products".
        # Se não usar, troque "products" por "product_set".
        return (
            Category.objects.all()
            .annotate(product_count=Count("products"))
            .order_by("name")
        )


# -------------------------
# Produtos (CRUD)
# -------------------------
class ProductViewSet(viewsets.ModelViewSet):
    serializer_class = ProductSerializer
    queryset = Product.objects.all().select_related("category").order_by("-id")

    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "sku", "description"]
    ordering_fields = ["id", "name", "price_cents", "stock", "created_at"]

    def get_queryset(self):
        qs = super().get_queryset()
        category_id = self.request.query_params.get("category_id")
        category = self.request.query_params.get("category")
        category_slug = self.request.query_params.get("category_slug")
        if category_id or category:
            qs = qs.filter(category_id=category_id or category)
        if category_slug:
            qs = qs.filter(category__slug=category_slug)
        return qs

    @action(detail=False, methods=["post"])
    def seed(self, request):
        """
        Cria produtos fake (respeita ENABLE_SEED ou DEBUG no settings).
        """
        from django.conf import settings
        if not (getattr(settings, "ENABLE_SEED", False) or settings.DEBUG):
            return Response({"detail": "Seed desabilitado."}, status=403)

        import random, string
        from .models import Product

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
    serializer_class = SupplierSerializer
    queryset = Supplier.objects.all().order_by("name")
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "email", "contact_person", "phone"]
    ordering_fields = ["name", "created_at", "updated_at"]


# -------------------------
# Pedidos (CRUD)
# -------------------------
class OrderViewSet(viewsets.ModelViewSet):
    """
    POST -> OrderCreateSerializer (escrita)
    GET/PUT/PATCH -> OrderReadSerializer (leitura)
    """
    queryset = (
        Order.objects.all()
        .prefetch_related("items__product")
        .order_by("-created_at")
    )
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ["created_at", "total_price_cents", "status"]

    def get_serializer_class(self):
        if self.action in ("create",):
            return OrderCreateSerializer
        return OrderReadSerializer
