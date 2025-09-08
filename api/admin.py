# api/admin.py
from django.contrib import admin
from django.utils.safestring import mark_safe
from .models import Category, Product, Supplier, Order, OrderItem, ProductMedia
from .forms import ProductAdminForm


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "slug", "created_at")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}


class ProductMediaInline(admin.TabularInline):
    model = ProductMedia
    extra = 1
    fields = ("media_type", "file", "external_url", "alt_text", "sort_order", "preview")
    readonly_fields = ("preview",)

    def preview(self, obj):
        if not obj.pk:
            return "-"
        url = obj.file.url if obj.file else obj.external_url
        if not url:
            return "-"
        if obj.media_type == "image":
            return mark_safe(f'<img src="{url}" style="height:60px;width:60px;object-fit:cover;border-radius:6px;" />')
        return mark_safe(f'<a href="{url}" target="_blank" rel="noopener">ver vídeo</a>')


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    form = ProductAdminForm  # <<< usa o form com preço em reais
    list_display = ("id", "name", "sku", "price_fmt", "stock", "category", "thumb")
    list_filter = ("category",)
    search_fields = ("name", "sku", "description")
    inlines = [ProductMediaInline]
    readonly_fields = ("thumb_preview",)

    fieldsets = (
        (None, {"fields": ("name", "sku", "description", "category", "stock")}),
        ("Preço", {"fields": ("price_reais", "price_cents")}),  # price_cents fica oculto pelo form
        ("Imagem principal / URL externa", {"fields": ("image", "image_url", "thumb_preview")}),
    )

    def price_fmt(self, obj):
        return f"R$ {obj.price_cents / 100:.2f}".replace(".", ",")
    price_fmt.short_description = "Preço"

    def thumb(self, obj):
        url = obj.primary_image_url()
        if not url:
            return "-"
        return mark_safe(f'<img src="{url}" style="height:40px;width:40px;object-fit:cover;border-radius:6px;" />')
    thumb.short_description = "Thumb"

    def thumb_preview(self, obj):
        url = obj.primary_image_url()
        if not url:
            return "—"
        return mark_safe(
            f'<img src="{url}" style="max-width:240px;height:auto;border-radius:8px;box-shadow:0 1px 3px rgba(0,0,0,.15)" />'
        )


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "email", "phone", "created_at")
    search_fields = ("name", "email", "phone")


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("price_cents",)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "customer_name", "status", "total_price_cents", "created_at")
    list_filter = ("status",)
    search_fields = ("customer_name",)
    inlines = [OrderItemInline]
