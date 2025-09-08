# api/serializers.py — produtos + pedido com SERIALIZERS separados (write/read) e validações robustas

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
    # Usa annotate se vier, senão calcula .products.count()
    product_count = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ["id", "name", "slug", "created_at", "product_count"]

    def get_product_count(self, obj):
        try:
            return getattr(obj, "product_count", None) or obj.products.count()
        except Exception:
            return 0


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
        cents = int(obj.price_cents or 0)
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
    # Recebemos product_id no payload e resolvemos para Product
    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(),
        source="product",
        write_only=True,
    )

    class Meta:
        model = OrderItem
        fields = ("product_id", "quantity")  # price_cents calculado no servidor

    def validate_quantity(self, value):
        try:
            q = int(value)
        except Exception:
            raise serializers.ValidationError("Quantidade inválida.")
        if q <= 0:
            raise serializers.ValidationError("Quantidade deve ser ≥ 1.")
        return q


class OrderCreateSerializer(serializers.ModelSerializer):
    items = OrderItemWriteSerializer(many=True)

    class Meta:
        model = Order
        fields = (
            "id",
            "customer_name",
            "status",              # opcional; default do model = "pending"
            "total_price_cents",   # read-only no create (será calculado)
            "items",
            "created_at",
            "updated_at",
        )
    # id/total/created/updated são controlados pelo servidor
    read_only_fields = ("id", "total_price_cents", "created_at", "updated_at")

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError("Informe ao menos 1 item.")
        return value

    @transaction.atomic
    def create(self, validated_data):
        """
        Criação transacional de Order + OrderItems.
        - resolve product_id -> product (já feito pelo serializer filho)
        - fixa price_cents no momento do pedido
        - soma total_price_cents
        """
        items_data = validated_data.pop("items", [])
        # status respeita o default "pending" do model, a menos que venha no payload
        order = Order.objects.create(**validated_data)

        total_cents = 0
        for idx, item in enumerate(items_data):
            product = item["product"]          # já é instancia de Product
            qty = int(item.get("quantity") or 1)
            price_cents = int(product.price_cents or 0)

            OrderItem.objects.create(
                order=order,
                product=product,
                quantity=qty,
                price_cents=price_cents,
            )
            total_cents += price_cents * qty

        order.total_price_cents = total_cents
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
        reais = cents / 100.0
        return f"R$ {reais:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")











