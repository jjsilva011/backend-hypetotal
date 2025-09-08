# api/serializers.py — produtos + pedido com SERIALIZERS separados p/ escrita/leitura
# Objetivo: POST /api/orders/ nunca estourar 500; sempre retornar 400 com mensagens claras.

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
    # Em DBs sem annotate(product_count) evitamos AttributeError:
    product_count = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ["id", "name", "slug", "created_at", "product_count"]

    def get_product_count(self, obj):
        try:
            return int(getattr(obj, "product_count", 0) or 0)
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
        cents = int(getattr(obj, "price_cents", 0) or 0)
        reais = cents // 100
        cent = cents % 100
        return f"R$ {reais:,},{cent:02d}".replace(",", "X").replace(".", ",").replace("X", ".")

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
        qty = attrs.get("quantity")
        try:
            qty = int(qty)
        except Exception:
            raise serializers.ValidationError({"quantity": "Deve ser um inteiro ≥ 1"})
        if qty < 1:
            raise serializers.ValidationError({"quantity": "Deve ser ≥ 1"})
        attrs["quantity"] = qty
        return attrs


class OrderCreateSerializer(serializers.ModelSerializer):
    items = OrderItemWriteSerializer(many=True)

    class Meta:
        model = Order
        fields = ("id", "customer_name", "status", "total_price_cents", "items", "created_at", "updated_at")
        read_only_fields = ("id", "status", "total_price_cents", "created_at", "updated_at")

    @transaction.atomic
    def create(self, validated_data):
        """
        Estratégia "blind-safe":
        - Valida tudo antes de gravar.
        - Converte e verifica product_id/quantity.
        - Captura erros e transforma em 400 legíveis.
        """
        items_data = list(validated_data.pop("items", []))
        if not items_data:
            raise serializers.ValidationError({"items": "Obrigatório e não pode ser vazio."})

        customer_name = (validated_data.get("customer_name") or "").strip()
        if not customer_name:
            raise serializers.ValidationError({"customer_name": "Obrigatório."})

        # 1) Resolver itens (sem gravar nada ainda)
        resolved = []
        total = 0

        # Import local para evitar ciclos em ambientes onde import na carga do módulo dá pau
        from .models import Product, OrderItem  # noqa

        for idx, item in enumerate(items_data, start=1):
            # product_id
            pid = item.get("product_id", None)
            try:
                pid_int = int(pid)
            except Exception:
                raise serializers.ValidationError({"items": [{ "index": idx, "product_id": "Inválido" }]})

            try:
                product = Product.objects.get(pk=pid_int)
            except Product.DoesNotExist:
                raise serializers.ValidationError({"items": [{ "index": idx, "product_id": f"Inexistente: {pid}" }]})

            # quantity
            qty = item.get("quantity", 0)
            try:
                qty = int(qty)
            except Exception:
                raise serializers.ValidationError({"items": [{ "index": idx, "quantity": "Inválido" }]})
            if qty < 1:
                raise serializers.ValidationError({"items": [{ "index": idx, "quantity": "Deve ser ≥ 1" }]})

            price = int(product.price_cents or 0)
            resolved.append((product, qty, price))
            total += price * qty

        # 2) Persistir pedido e itens
        order = Order.objects.create(
            customer_name=customer_name,
            status="pending",
            total_price_cents=0,  # atualizaremos depois
        )

        OrderItem.objects.bulk_create([
            OrderItem(order=order, product=p, quantity=q, price_cents=pc)
            for (p, q, pc) in resolved
        ])

        # Atualiza total por UPDATE (menos chance de race condition)
        Order.objects.filter(pk=order.pk).update(total_price_cents=total)
        order.refresh_from_db()
        return order

    def to_representation(self, instance):
        # Após criar, devolvemos o formato de leitura completo (com itens + product)
        return OrderReadSerializer(instance, context=self.context).data


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
        cents = int(getattr(obj, "total_price_cents", 0) or 0)
        reais = cents // 100
        cent = cents % 100
        return f"R$ {reais:,},{cent:02d}".replace(",", "X").replace(".", ",").replace("X", ".")













