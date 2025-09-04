# api/serializers.py (Versão Corrigida)
from rest_framework import serializers
from .models import Product, Supplier, Order, OrderItem

# --- Serializadores existentes (sem alterações) ---
class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = [
            "id", "name", "sku", "description", "price_cents", "stock", "created_at",
        ]
        read_only_fields = ["id", "created_at"]

class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = [
            'id', 'name', 'contact_person', 'email', 'phone', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

# --- Serializadores de Pedidos (COM CORREÇÕES) ---

# Serializador para os itens DENTRO de um pedido.
# Usado para criar e ler os itens.
class OrderItemSerializer(serializers.ModelSerializer):
    # Usamos um campo 'product_id' que só aceita a escrita (write_only).
    # Isso permite que o frontend envie apenas o ID do produto, que é o que ele tem.
    product_id = serializers.IntegerField(write_only=True)
    
    # Para leitura (read_only), mostramos os detalhes do produto.
    product = ProductSerializer(read_only=True)

    class Meta:
        model = OrderItem
        # O campo 'order' não é mais necessário aqui, pois ele será gerenciado pelo OrderSerializer.
        fields = ['id', 'product_id', 'product', 'quantity', 'price_cents']
        read_only_fields = ['id', 'price_cents', 'product']

# Serializador principal para o Pedido.
class OrderSerializer(serializers.ModelSerializer):
    # Define que o campo 'items' usará o OrderItemSerializer e pode ter múltiplos itens.
    items = OrderItemSerializer(many=True)
    
    # Para leitura, mostra o total formatado.
    total_price_formatted = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            'id', 'customer_name', 'status', 'total_price_cents', 
            'total_price_formatted', 'created_at', 'updated_at', 'items'
        ]
        read_only_fields = ['id', 'total_price_cents', 'total_price_formatted', 'created_at', 'updated_at']

    def get_total_price_formatted(self, obj):
        # Formata o preço para "R$ 123,45"
        return f"R$ {(obj.total_price_cents / 100):.2f}".replace('.', ',')

    # A mágica acontece aqui, no método create.
    def create(self, validated_data):
        # Pega os dados dos itens que foram validados.
        items_data = validated_data.pop('items')
        
        # Cria o objeto Order com os dados principais.
        order = Order.objects.create(**validated_data)
        
        total_price = 0
        # Itera sobre cada item enviado pelo frontend.
        for item_data in items_data:
            product_id = item_data['product_id']
            quantity = item_data['quantity']
            product = Product.objects.get(id=product_id)
            
            # Cria o OrderItem, associando-o ao pedido que acabamos de criar.
            OrderItem.objects.create(
                order=order,
                product=product,
                quantity=quantity,
                price_cents=product.price_cents # Salva o preço no momento da compra.
            )
            total_price += product.price_cents * quantity

        # Atualiza o preço total do pedido e o salva.
        order.total_price_cents = total_price
        order.save()
        
        return order


