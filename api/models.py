# api/models.py — modelos com Category, Product, ProductMedia, Supplier, Order, OrderItem e Customer
from django.db import models
from django.utils import timezone

# --------- Categorias ---------
class Category(models.Model):
    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=140, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


# --------- Produtos ---------
class Product(models.Model):
    name = models.CharField(max_length=255)
    sku = models.CharField(max_length=40, unique=True)
    description = models.TextField(blank=True, default="")
    category = models.ForeignKey(
        Category, related_name="products", on_delete=models.SET_NULL, null=True, blank=True
    )

    # preço armazenado em centavos (inteiro)
    price_cents = models.PositiveIntegerField(default=0)
    stock = models.PositiveIntegerField(default=0)

    # mídia principal (opcional)
    image = models.ImageField(upload_to="products/", blank=True, null=True)
    image_url = models.URLField(blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-id"]

    def __str__(self):
        return f"{self.name} ({self.sku})"

    def primary_image_url(self) -> str:
        """
        Regras de prioridade:
        1) arquivo de imagem principal (self.image)
        2) image_url
        3) primeira mídia do tipo 'image' em ProductMedia
        """
        if self.image:
            try:
                return self.image.url
            except Exception:
                pass
        if self.image_url:
            return self.image_url
        first_media = self.media.filter(media_type="image").order_by("sort_order", "id").first()
        if first_media:
            if first_media.file:
                try:
                    return first_media.file.url
                except Exception:
                    pass
            if first_media.external_url:
                return first_media.external_url
        return ""


# --------- Galeria (imagens/vídeos por produto) ---------
class ProductMedia(models.Model):
    MEDIA_CHOICES = (
        ("image", "Imagem"),
        ("video", "Vídeo"),
    )

    product = models.ForeignKey(Product, related_name="media", on_delete=models.CASCADE)
    media_type = models.CharField(max_length=10, choices=MEDIA_CHOICES, default="image")

    # Você pode subir arquivo (imagem/vídeo curto) OU apontar uma URL externa (YouTube/Vimeo/etc.)
    file = models.FileField(upload_to="products/media/", blank=True, null=True)
    external_url = models.URLField(blank=True, default="")
    alt_text = models.CharField(max_length=200, blank=True, default="")
    sort_order = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["sort_order", "id"]

    def __str__(self):
        kind = "IMG" if self.media_type == "image" else "VID"
        return f"[{kind}] {self.product.name} #{self.pk}"


# --------- Fornecedores ---------
class Supplier(models.Model):
    name = models.CharField(max_length=255, unique=True, help_text="Nome do fornecedor")
    contact_person = models.CharField(max_length=255, blank=True, help_text="Pessoa de contato")
    email = models.EmailField(max_length=255, unique=True, help_text="E-mail")
    phone = models.CharField(max_length=20, blank=True, help_text="Telefone")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


# --------- Pedidos ---------
class Order(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pendente"),
        ("paid", "Pago"),
        ("processing", "Processando"),
        ("shipped", "Enviado"),
        ("delivered", "Entregue"),
        ("canceled", "Cancelado"),
        ("failed", "Falhou"),
    ]

    # Campos de pagamento adicionais (já previstos na nossa etapa anterior)
    PAYMENT_PROVIDER_CHOICES = [
        ("mercadopago", "Mercado Pago"),
        ("", "N/D"),
    ]

    customer_name = models.CharField(max_length=255, help_text="Nome do cliente")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    total_price_cents = models.PositiveIntegerField(default=0, help_text="Preço total em centavos")
    payment_provider = models.CharField(max_length=30, choices=PAYMENT_PROVIDER_CHOICES, blank=True, default="")
    payment_reference = models.CharField(max_length=120, blank=True, default="")
    external_reference = models.CharField(max_length=120, blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Pedido #{self.id} - {self.customer_name}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name="items", on_delete=models.CASCADE)
    product = models.ForeignKey(Product, related_name="order_items", on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(default=1)
    # preço do item no momento do pedido (em centavos)
    price_cents = models.PositiveIntegerField(help_text="Preço do item em centavos à época do pedido")

    def __str__(self):
        return f"{self.quantity}x {self.product.name} no Pedido #{self.order.id}"


# --------- Clientes ---------
class Customer(models.Model):
    """
    Cliente com verificação de e-mail e telefone.
    Em DEV, o endpoint de registro retorna os tokens/OTP para facilitar o teste.
    """
    name = models.CharField(max_length=255)
    email = models.EmailField(max_length=255, unique=True, db_index=True)
    # Telefone em E.164 (ex.: +5511999999999). Não impomos unique=True agora para não travar duplicidade em DEV.
    phone = models.CharField(max_length=20, blank=True, default="", db_index=True)

    is_email_verified = models.BooleanField(default=False)
    is_phone_verified = models.BooleanField(default=False)

    # Token e-mail (link)
    email_verification_token = models.CharField(max_length=120, blank=True, default="")
    email_token_created_at = models.DateTimeField(null=True, blank=True)

    # OTP telefone (6 dígitos) com expiração
    phone_otp_code = models.CharField(max_length=6, blank=True, default="")
    phone_otp_expires_at = models.DateTimeField(null=True, blank=True)
    phone_otp_attempts = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} <{self.email}>"

    def email_token_is_valid(self, token: str) -> bool:
        if not token or not self.email_verification_token:
            return False
        if token.strip() != self.email_verification_token.strip():
            return False
        # opcional: expiração (ex.: 48h). Aqui aceitamos se existe.
        return True

    def phone_otp_is_valid(self, code: str) -> bool:
        if not code or not self.phone_otp_code:
            return False
        if code.strip() != self.phone_otp_code.strip():
            return False
        if not self.phone_otp_expires_at:
            return False
        return timezone.now() <= self.phone_otp_expires_at













