# api/views.py — ViewSets + Fallbacks (categories, orders.safe)

from django.db.models import Count
from django.db import transaction
from django.http import JsonResponse, HttpRequest
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

from .models import Product, Supplier, Order, Category, OrderItem
from .serializers import (
    ProductSerializer,
    SupplierSerializer,
    OrderReadSerializer,
    OrderCreateSerializer,
    CategorySerializer,
)

# -------------------------------------------------
# Categorias (ViewSet normal usado pelo router)
# -------------------------------------------------
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


# -------------------------------------------------
# Produtos (CRUD)
# -------------------------------------------------
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
        category_id   = qp.get("category_id") or qp.get("category")
        category_slug = qp.get("category_slug")
        if category_id:
            qs = qs.filter(category_id=category_id)
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


# -------------------------------------------------
# Fornecedores (CRUD)
# -------------------------------------------------
class SupplierViewSet(viewsets.ModelViewSet):
    permission_classes = [AllowAny]
    serializer_class = SupplierSerializer
    queryset = Supplier.objects.all().order_by("name")
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "email", "contact_person", "phone"]
    ordering_fields = ["name", "created_at", "updated_at"]


# -------------------------------------------------
# Pedidos (CRUD) — leitura e escrita separadas
# -------------------------------------------------
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
        ser = OrderReadSerializer(page or qs, many=True, context={"request": request})
        if page is not None:
            return self.get_paginated_response(ser.data)
        return Response(ser.data)

    def retrieve(self, request, *args, **kwargs):
        obj = self.get_object()
        data = OrderReadSerializer(obj, context={"request": request}).data
        return Response(data)

    def create(self, request, *args, **kwargs):
        ser = OrderCreateSerializer(data=request.data, context={"request": request})
        if not ser.is_valid():
            return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)
        try:
            order = ser.save()
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


# =========================================================
# FALLBACKS (não dependem do router) — usados pelo projeto
# =========================================================

def categories_list_fallback(_request: HttpRequest):
    """
    /api/categories/ — funciona mesmo se o router não registrou.
    Retorna: [{id,name,slug,product_count}]
    """
    rel = "products"
    try:
        Category._meta.get_field("products")  # type: ignore[attr-defined]
    except Exception:
        rel = "product_set"

    qs = Category.objects.all().annotate(product_count=Count(rel)).order_by("name")
    data = CategorySerializer(qs, many=True).data
    return JsonResponse(data, safe=False)


def orders_list_safe(_request: HttpRequest):
    """
    /api/orders.safe/ — lista segura (sem serializers encadeados) para eliminar 500.
    Inclui itens com product_id, quantity, price_cents.
    """
    out = []
    qs = Order.objects.all().order_by("-created_at")[:200]
    items_by_order = {}
    for it in OrderItem.objects.filter(order_id__in=[o.id for o in qs]):
        items_by_order.setdefault(it.order_id, []).append({
            "product_id": it.product_id,
            "quantity": int(it.quantity or 0),
            "price_cents": int(it.price_cents or 0),
        })
    for o in qs:
        out.append({
            "id": o.id,
            "customer_name": o.customer_name,
            "status": o.status,
            "total_price_cents": int(o.total_price_cents or 0),
            "created_at": o.created_at,
            "items": items_by_order.get(o.id, []),
        })
    return JsonResponse(out, safe=False)


def orders_create_safe(request: HttpRequest):
    """
    /api/orders.safe/create — cria pedido de forma robusta.
    Body: { "customer_name": "...", "items": [ { "product_id": 31, "quantity": 1 }, ... ] }
    """
    if request.method != "POST":
        return JsonResponse({"detail": "Method not allowed"}, status=405)

    data = getattr(request, "data", None) or {}
    name = (data.get("customer_name") or "").strip() or "Cliente"
    raw_items = data.get("items") or []
    if not isinstance(raw_items, list) or not raw_items:
        return JsonResponse({"detail": "items obrigatórios."}, status=400)

    items = []
    for it in raw_items:
        try:
            pid = int(it.get("product_id"))
            qty = int(it.get("quantity") or 0)
        except Exception:
            continue
        if qty <= 0:
            continue
        p = Product.objects.filter(pk=pid).first()
        if not p:
            return JsonResponse({"detail": f"Produto {pid} não encontrado."}, status=400)
        items.append((p, qty, int(p.price_cents or 0)))
    if not items:
        return JsonResponse({"detail": "Nenhum item válido."}, status=400)

    with transaction.atomic():
        o = Order.objects.create(customer_name=name, status="pending", total_price_cents=0)
        total = 0
        for p, qty, price in items:
            OrderItem.objects.create(order=o, product=p, quantity=qty, price_cents=price)
            total += qty * price
        o.total_price_cents = total
        o.save(update_fields=["total_price_cents"])

    return JsonResponse({
        "id": o.id,
        "customer_name": o.customer_name,
        "status": o.status,
        "total_price_cents": o.total_price_cents,
        "created_at": o.created_at,
        "items": [{"product_id": p.id, "quantity": qty, "price_cents": price} for p, qty, price in items],
    }, status=201)





