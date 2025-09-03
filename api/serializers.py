# api/serializers.py
from rest_framework import serializers
from .models import Product, Supplier, Order, OrderItem # Importa os novos modelos

class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "sku",
            "description",
            "price_cents",
            "stock",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]

class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = [
            'id',
            'name',
            'contact_person',
            'email',
            'phone',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

# --- ADICIONE OS SERIALIZADORES DE PEDIDO ABAIXO ---

class OrderItemSerializer(serializers.ModelSerializer):
    # Usamos um ProductSerializer aninhado para mostrar os detalhes do produto
    product = ProductSerializer(read_only=True)
    # Campo para receber o ID do produto ao criar/atualizar um item
    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(), source='product', write_only=True
    )

    class Meta:
        model = OrderItem
        fields = [
            'id',
            'product',
            'product_id', # Apenas para escrita
            'quantity',
            'price_cents_at_time_of_order'
        ]
        read_only_fields = ['id', 'price_cents_at_time_of_order']


class OrderSerializer(serializers.ModelSerializer):
    # 'items' é o related_name que definimos no modelo OrderItem
    # many=True indica que um pedido pode ter vários itens
    # read_only=True porque vamos criar os itens de uma forma especial
    items = OrderItemSerializer(many=True, read_only=True)

    # Campo para receber a lista de itens ao criar um pedido
    # Ex: "order_items": [{"product_id": 1, "quantity": 2}, {"product_id": 3, "quantity": 1}]
    order_items = serializers.ListField(
        child=serializers.DictField(), write_only=True
    )

    class Meta:
        model = Order
        fields = [
            'id',
            'customer_name',
            'status',
            'total_price_cents',
            'created_at',
            'updated_at',
            'items', # Para leitura
            'order_items' # Apenas para escrita
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'total_price_cents']

    def create(self, validated_data):
        # Remove os dados dos itens do dicionário principal
        order_items_data = validated_data.pop('order_items')
        
        # Cria o objeto Order
        order = Order.objects.create(**validated_data)
        
        total_price = 0
        # Itera sobre os itens para criar os objetos OrderItem
        for item_data in order_items_data:
            product = item_data['product']
            quantity = item_data['quantity']
            
            # Cria o OrderItem associado ao pedido
            OrderItem.objects.create(
                order=order,
                product=product,
                quantity=quantity,
                # Salva o preço do produto no momento da compra
                price_cents_at_time_of_order=product.price_cents
            )
            # Atualiza o preço total do pedido
            total_price += product.price_cents * quantity

        # Atualiza o preço total no objeto Order e salva
        order.total_price_cents = total_price
        order.save()
        
        return order


