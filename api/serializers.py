# api/serializers.py — produtos + pedido (WRITE/READ) com create() blindado contra 500

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
        fields = ("product_id", "quantity")  # price_cents é calculado no servidor

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
        - converte qualquer falha inesperada em 400 com mensagem legível (nada de 500)
        """
        try:
            items_data = validated_data.pop("items", [])
            if not items_data:
                raise serializers.ValidationError({"items": "Obrigatório e não pode ser vazio."})

            # cria o pedido (status default = pending, salvo se cliente mandar)
            order = Order.objects.create(**validated_data)

            total_cents = 0
            for idx, item in enumerate(items_data, start=1):
                product = item.get("product")
                if not isinstance(product, Product):
                    raise serializers.ValidationError({
                        "items": {idx - 1: {"product_id": "Produto inválido ou inexistente."}}
                    })

                qty = int(item.get("quantity") or 1)
                if qty <= 0:
                    raise serializers.ValidationError({
                        "items": {idx - 1: {"quantity": "Quantidade deve ser ≥ 1."}}
                    })

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

        except Product.DoesNotExist:
            # não deve acontecer porque PKRelatedField já valida, mas sejamos explícitos
            raise serializers.ValidationError({"items": "Produto informado não existe."})
        except serializers.ValidationError:
            # repassa validações amigáveis
            raise
        except Exception as e:
            # último guarda-chuva: transforma 500 em 400 com mensagem
            raise serializers.ValidationError({"detail": f"Falha ao criar pedido: {str(e)}"})


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












