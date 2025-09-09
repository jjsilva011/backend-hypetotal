# api/admin.py
from django.contrib import admin
from django.utils.safestring import mark_safe

# --- Importa o form de produto (com fallback caso falhe o import) ---
try:
    from .forms import ProductAdminForm  # mostra/edita preço em reais
except Exception:
    ProductAdminForm = None  # Admin continua funcional sem o form

# --- Modelos ---
from .models import Category, Product, Supplier, Order, OrderItem, ProductMedia


# ===============================
# Category
# ===============================
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "slug", "created_at")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}


# ===============================
# ProductMedia (inline)
# ===============================
class ProductMediaInline(admin.TabularInline):
    model = ProductMedia
    extra = 1
    fields = ("media_type", "file", "external_url", "alt_text", "sort_order", "preview")
    readonly_fields = ("preview",)

    def preview(self, obj):
        try:
            if not getattr(obj, "pk", None):
                return "—"
            url = ""
            f = getattr(obj, "file", None)
            if f and getattr(f, "name", ""):
                # FieldFile com nome definido -> tenta url
                try:
                    url = f.url
                except Exception:
                    url = ""
            if not url:
                url = getattr(obj, "external_url", "") or ""
            if not url:
                return "—"
            if getattr(obj, "media_type", "") == "image":
                return mark_safe(
                    f'<img src="{url}" style="height:60px;width:60px;object-fit:cover;border-radius:6px;" />'
                )
            return mark_safe(f'<a href="{url}" target="_blank" rel="noopener">ver mídia</a>')
        except Exception:
            return "—"


# ===============================
# Helpers de apresentação
# ===============================
def _best_image_url(p: Product) -> str:
    """Melhor esforço para obter uma URL de imagem do produto."""
    # 1) Método do modelo, se existir
    try:
        primary = getattr(p, "primary_image_url", None)
        if callable(primary):
            url = primary()
            if url:
                return str(url)
    except Exception:
        pass

    # 2) Campo ImageField local
    try:
        img = getattr(p, "image", None)
        if img and getattr(img, "name", ""):
            try:
                return str(img.url)
            except Exception:
                pass
    except Exception:
        pass

    # 3) Campo image_url (texto) externo
    try:
        url = getattr(p, "image_url", "") or ""
        if url:
            return str(url)
    except Exception:
        pass

    return ""


def _price_fmt_from_cents(obj) -> str:
    try:
        cents = int(getattr(obj, "price_cents", 0) or 0)
        return f"R$ {cents / 100:.2f}".replace(".", ",")
    except Exception:
        return "—"


# ===============================
# Product
# ===============================
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    # Usa o form com preço em reais se disponível; senão, form padrão
    if ProductAdminForm:
        form = ProductAdminForm

    list_display = ("id", "name", "sku", "price_fmt", "stock", "category", "thumb")
    list_filter = ("category",)
    search_fields = ("name", "sku", "description")
    inlines = [ProductMediaInline]
    readonly_fields = ("thumb_preview",)

    # fieldsets dinâmicos para não quebrar se algum campo não existir
    def get_fieldsets(self, request, obj=None):
        model_fields = {f.name for f in self.model._meta.get_fields()}

        basics = [f for f in ("name", "sku", "description", "category", "stock") if f in model_fields]

        price_group = []
        # Campo virtual exibido pelo form; mesmo sem form mantemos a chave no group
        price_group.append("price_reais")
        if "price_cents" in model_fields:
            price_group.append("price_cents")

        media_group = []
        if "image" in model_fields:
            media_group.append("image")
        if "image_url" in model_fields:
            media_group.append("image_url")
        media_group.append("thumb_preview")  # método do admin

        fieldsets = []
        if basics:
            fieldsets.append((None, {"fields": tuple(basics)}))
        if price_group:
            fieldsets.append(("Preço", {"fields": tuple(price_group)}))
        if media_group:
            fieldsets.append(("Imagem principal / URL externa", {"fields": tuple(media_group)}))
        return tuple(fieldsets)

    # Colunas calculadas
    def price_fmt(self, obj):
        return _price_fmt_from_cents(obj)
    price_fmt.short_description = "Preço"

    def thumb(self, obj):
        try:
            url = _best_image_url(obj)
            if not url:
                return "—"
            return mark_safe(
                f'<img src="{url}" style="height:40px;width:40px;object-fit:cover;border-radius:6px;" />'
            )
        except Exception:
            return "—"
    thumb.short_description = "Thumb"

    def thumb_preview(self, obj):
        try:
            url = _best_image_url(obj)
            if not url:
                return "—"
            return mark_safe(
                f'<img src="{url}" style="max-width:240px;height:auto;border-radius:8px;'
                f'box-shadow:0 1px 3px rgba(0,0,0,.15)" />'
            )
        except Exception:
            return "—"


# ===============================
# Supplier
# ===============================
@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "email", "phone", "created_at")
    search_fields = ("name", "email", "phone")


# ===============================
# Order / OrderItem
# ===============================
class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    # Só marca como readonly se o campo existir
    readonly_fields = tuple(
        f for f in ("price_cents",)
        if f in {fld.name for fld in OrderItem._meta.get_fields()}
    )


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "customer_name", "status", "total_price_cents", "created_at")
    list_filter = ("status",)
    search_fields = ("customer_name",)
    inlines = [OrderItemInline]

