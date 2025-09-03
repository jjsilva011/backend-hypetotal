# api/models.py
from django.db import models

class Product(models.Model):
    name = models.CharField(max_length=255)
    sku = models.CharField(max_length=40, unique=True)
    description = models.TextField(blank=True, default="")
    price_cents = models.PositiveIntegerField(default=0)
    stock = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-id"]

    def __str__(self):
        return f"{self.name} ({self.sku})"

class Supplier(models.Model):
    name = models.CharField(max_length=255, unique=True, help_text="Nome do fornecedor")
    contact_person = models.CharField(max_length=255, blank=True, help_text="Nome da pessoa de contato")
    email = models.EmailField(max_length=255, unique=True, help_text="E-mail para contato")
    phone = models.CharField(max_length=20, blank=True, help_text="Telefone para contato")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']

# --- ADICIONE OS MODELOS DE PEDIDO ABAIXO ---

class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pendente'),
        ('processing', 'Processando'),
        ('shipped', 'Enviado'),
        ('delivered', 'Entregue'),
        ('canceled', 'Cancelado'),
    ]

    customer_name = models.CharField(max_length=255, help_text="Nome do cliente")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    total_price_cents = models.PositiveIntegerField(default=0, help_text="Preço total em centavos")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Pedido #{self.id} - {self.customer_name}"

class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, related_name='order_items', on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(default=1)
    price_cents_at_time_of_order = models.PositiveIntegerField(help_text="Preço do item em centavos no momento do pedido")

    def __str__(self):
        return f"{self.quantity}x {self.product.name} no Pedido #{self.order.id}"





