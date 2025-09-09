# api/forms.py
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from django import forms
from .models import Product


def _parse_reais(raw: str) -> Decimal:
    """
    Converte strings como 'R$ 1.234,56', '36,90', '36.90', '36' em Decimal(2 casas).
    Regras:
      - remove 'R$', espaços e separador de milhar
      - vírgula vira ponto como separador decimal
    """
    s = (raw or "").strip()
    if not s:
        return Decimal("0.00")
    s = s.replace("R$", "").replace(" ", "")

    # Se vier no formato '1.234,56'
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    # Se vier só com vírgula decimal '36,90'
    elif "," in s:
        s = s.replace(",", ".")

    try:
        val = Decimal(s)
    except InvalidOperation:
        raise forms.ValidationError("Valor inválido. Use algo como 129,90.")

    if val < 0:
        raise forms.ValidationError("Preço não pode ser negativo.")

    return val.quantize(Decimal("0.01"))


class ProductAdminForm(forms.ModelForm):
    """
    Mostra 'Preço (R$)' (aceita 36, 36,9, 36,90, 36.90, 1.234,56) e salva em price_cents.
    Oculta o campo técnico price_cents no admin (quando existir no modelo).
    Também valida 'stock' >= 0 quando presente.
    """
    price_reais = forms.CharField(
        label="Preço (R$)",
        required=False,
        help_text="Ex.: 129,90",
    )

    class Meta:
        model = Product
        # Usamos __all__ para evitar quebrar se o modelo mudar (ex.: sem 'image').
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Preenche o campo de exibição em reais a partir de price_cents, se existir.
        cents = 0
        if hasattr(self.instance, "price_cents") and self.instance.pk:
            try:
                cents = int(self.instance.price_cents or 0)
            except Exception:
                cents = 0
        self.fields["price_reais"].initial = (
            f"{Decimal(cents) / 100:.2f}".replace(".", ",")
        )

        # Esconde o campo técnico se ele existir no ModelForm
        if "price_cents" in self.fields:
            self.fields["price_cents"].widget = forms.HiddenInput()
            self.fields["price_cents"].required = False

        # Ajuda visual (não obrigatório): placeholders amigáveis
        if "sku" in self.fields:
            self.fields["sku"].help_text = (self.fields["sku"].help_text or "") + " "
            self.fields["sku"].help_text += "Identificador único do produto."

        if "image_url" in self.fields:
            self.fields["image_url"].help_text = (self.fields["image_url"].help_text or "") + " "
            self.fields["image_url"].help_text += "URL da imagem (se usar mídia externa)."

    def clean_price_reais(self):
        raw = (self.cleaned_data.get("price_reais") or "").strip()
        return _parse_reais(raw)

    def clean_stock(self):
        # Só valida se o campo existir no form
        if "stock" not in self.cleaned_data:
            return self.cleaned_data.get("stock")
        try:
            v = int(self.cleaned_data.get("stock") or 0)
        except Exception:
            raise forms.ValidationError("stock deve ser um número inteiro.")
        if v < 0:
            raise forms.ValidationError("stock não pode ser negativo.")
        return v

    def clean(self):
        cleaned = super().clean()
        reais = cleaned.get("price_reais", Decimal("0.00"))
        cents = int((reais * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))

        # Só seta se o campo existir no form/modelo
        if "price_cents" in self.fields:
            cleaned["price_cents"] = cents
        return cleaned

    def save(self, commit=True):
        # Garante que price_cents vai para a instância, se existir
        instance = super().save(commit=False)
        if hasattr(instance, "price_cents"):
            reais = self.cleaned_data.get("price_reais", Decimal("0.00"))
            cents = int((reais * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
            instance.price_cents = cents

        if commit:
            instance.save()
            # Salva M2M se houver
            if hasattr(self, "save_m2m"):
                self.save_m2m()
        return instance

