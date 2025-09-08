# C:\Users\jails\OneDrive\Desktop\Backend HypeTotal\api\serializers.py
# api/serializers.py — produtos + pedido com SERIALIZERS separados para escrita/leitura (sem gambiarra)

from django.db import transaction
from rest_framework import serializers
from .models import (
    Category,
    Product,
    ProductMedia,
    Supplier,
    Order,
    OrderItem,
)

# --------- Categorias ---------
class CategorySerializer(serializers.ModelSerializer):
    product_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Category
        fields = ["id", "name", "slug", "created_at", "product_count"]

# --------- Mídia do Produto (imagens/vídeos) ---------
class ProductMediaSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = ProductMedia
        fields = [
            "id",
            "media_type",     # "image" | "video"
            "file_url",       # URL resolvida do arquivo (se houver)
            "external_url",   # YouTube/Vimeo/etc (opcional)
            "alt_text",
            "sort_order",
        ]

    def get_file_url(self, obj):
        try:
            return obj.file.url if obj.file else ""
        except Exception:
            return ""

# --------- Produto ---------
class ProductSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(),
        source="category",
        write_only=True,
        required=False,
        allow_null=True,
    )

    price_formatted = serializers.SerializerMethodField()
    primary_image_url = serializers.SerializerMethodField()
    media = ProductMediaSerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "sku",
            "description",
            "category",
            "category_id",
            "price_cents",
            "price_formatted",
            "stock",
            "image_url",          # URL manual (fallback)
            "primary_image_url",  # calculada
            "media",              # galeria
            "created_at",
        ]

    def get_price_formatted(self, obj):
        cents = obj.price_cents or 0
        reais = cents / 100.0
        return f"R$ {reais:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    def get_primary_image_url(self, obj):
        try:
            return obj.primary_image_url() or ""
        except Exception:
            return ""

# --------- Fornecedor ---------
class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = "__all__"

# ===========================
#  PEDIDO / ITENS (WRITE)
# ===========================
class OrderItemWriteSerializer(serializers.ModelSerializer):
    # recebemos product_id no payload
    product_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = OrderItem
        fields = ("id", "product_id", "quantity", "price_cents", "product")
        read_only_fields = ("id", "price_cents", "product")

    def validate(self, attrs):
        qty = int(attrs.get("quantity") or 0)
        if qty < 1:
            raise serializers.ValidationError({"quantity": "Deve ser ≥ 1"})
        return attrs

class OrderCreateSerializer(serializers.ModelSerializer):
    items = OrderItemWriteSerializer(many=True)

    class Meta:
        model = Order
        fields = ("id", "customer_name", "status", "total_price_cents", "items", "created_at", "updated_at")
        read_only_fields = ("id", "status", "total_price_cents", "created_at", "updated_at")

    @transaction.atomic
    def create(self, validated_data):
        items_data = validated_data.pop("items", [])
        if not items_data:
            raise serializers.ValidationError({"items": "Obrigatório e não pode ser vazio."})

        # cria pedido pendente
        order = Order.objects.create(
            customer_name=validated_data["customer_name"],
            status="pending",
            total_price_cents=0,
        )

        from .models import Product, OrderItem  # import local para evitar ciclos
        total = 0
        for item in items_data:
            # busca o produto e fixa preço do momento
            product = Product.objects.get(pk=item["product_id"])
            qty = int(item.get("quantity") or 1)
            price = int(product.price_cents or 0)
            OrderItem.objects.create(order=order, product=product, quantity=qty, price_cents=price)
            total += price * qty

        order.total_price_cents = total
        order.save(update_fields=["total_price_cents"])
        return order

# ===========================
#  PEDIDO / ITENS (READ)
# ===========================
class OrderItemReadSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)

    class Meta:
        model = OrderItem
        fields = ("id", "product", "quantity", "price_cents")

class OrderReadSerializer(serializers.ModelSerializer):
    items = OrderItemReadSerializer(many=True, read_only=True)
    total_price_formatted = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = (
            "id",
            "customer_name",
            "status",
            "total_price_cents",
            "total_price_formatted",
            "items",
            "created_at",
            "updated_at",
        )

    def get_total_price_formatted(self, obj):
        cents = int(obj.total_price_cents or 0)
        reais = cents // 100
        cent = cents % 100
        return f"R$ {reais:,},{cent:02d}".replace(",", "X").replace(".", ",").replace("X", ".")










