# api/customer_views.py — stubs funcionais para cadastro e verificação de cliente (DEV)
from __future__ import annotations

from datetime import timedelta
import secrets
import string

from django.utils import timezone
from django.db import transaction
from django.core.exceptions import ValidationError
from django.core.validators import validate_email

from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from .models import Customer


def _rand_token(n: int = 32) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(n))


def _rand_otp(n: int = 6) -> str:
    return "".join(secrets.choice(string.digits) for _ in range(n))


@api_view(["POST"])
@transaction.atomic
def register_customer(request):
    """
    DEV: cria/atualiza Customer e retorna tokens para teste de verificação.
    Payload esperado:
      {
        "name": "Fulano",
        "email": "fulano@example.com",
        "phone": "+5511999999999"   (opcional)
      }
    Retorna 201 (created) ou 200 (updated) com dados e tokens.
    """
    data = request.data or {}
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    phone = (data.get("phone") or "").strip()

    if not name:
        return Response({"name": ["Obrigatório."]}, status=status.HTTP_400_BAD_REQUEST)
    if not email:
        return Response({"email": ["Obrigatório."]}, status=status.HTTP_400_BAD_REQUEST)
    try:
        validate_email(email)
    except ValidationError:
        return Response({"email": ["Inválido."]}, status=status.HTTP_400_BAD_REQUEST)

    # cria ou atualiza
    cust, created = Customer.objects.get_or_create(email=email, defaults={"name": name, "phone": phone})
    if not created:
        # atualiza campos básicos se enviados
        changed = False
        if name and cust.name != name:
            cust.name = name
            changed = True
        if phone and cust.phone != phone:
            cust.phone = phone
            changed = True
        if changed:
            cust.save(update_fields=["name", "phone"])

    # gera tokens DEV
    cust.email_verification_token = _rand_token(40)
    cust.email_token_created_at = timezone.now()

    cust.phone_otp_code = _rand_otp(6)
    cust.phone_otp_expires_at = timezone.now() + timedelta(minutes=10)
    cust.phone_otp_attempts = 0
    cust.save()

    payload = {
        "id": cust.id,
        "name": cust.name,
        "email": cust.email,
        "phone": cust.phone,
        "is_email_verified": cust.is_email_verified,
        "is_phone_verified": cust.is_phone_verified,
        # DEV helpers (não exponha em PROD):
        "dev": {
            "email_verification_token": cust.email_verification_token,
            "phone_otp_code": cust.phone_otp_code,
            "phone_otp_expires_at": cust.phone_otp_expires_at.isoformat() if cust.phone_otp_expires_at else None,
        },
    }
    return Response(payload, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


@api_view(["POST"])
@transaction.atomic
def verify_email(request):
    """
    Confirma e-mail via token.
    Payload:
      { "email": "fulano@example.com", "token": "<token>" }
    """
    data = request.data or {}
    email = (data.get("email") or "").strip().lower()
    token = (data.get("token") or "").strip()

    if not email or not token:
        return Response({"detail": "email e token são obrigatórios."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        cust = Customer.objects.get(email=email)
    except Customer.DoesNotExist:
        return Response({"detail": "Cliente não encontrado."}, status=status.HTTP_404_NOT_FOUND)

    if not cust.email_token_is_valid(token):
        return Response({"detail": "Token inválido."}, status=status.HTTP_400_BAD_REQUEST)

    if not cust.is_email_verified:
        cust.is_email_verified = True
        cust.save(update_fields=["is_email_verified"])

    return Response({"ok": True, "is_email_verified": True})


@api_view(["POST"])
@transaction.atomic
def verify_phone(request):
    """
    Confirma telefone via OTP.
    Payload (qualquer um dos identificadores):
      { "email": "fulano@example.com", "code": "123456" }
      ou
      { "phone": "+5511999999999", "code": "123456" }
    """
    data = request.data or {}
    email = (data.get("email") or "").strip().lower()
    phone = (data.get("phone") or "").strip()
    code = (data.get("code") or "").strip()

    if not code:
        return Response({"detail": "code é obrigatório."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        if email:
            cust = Customer.objects.get(email=email)
        elif phone:
            cust = Customer.objects.get(phone=phone)
        else:
            return Response({"detail": "informe email ou phone."}, status=status.HTTP_400_BAD_REQUEST)
    except Customer.DoesNotExist:
        return Response({"detail": "Cliente não encontrado."}, status=status.HTTP_404_NOT_FOUND)

    if not cust.phone_otp_is_valid(code):
        cust.phone_otp_attempts = (cust.phone_otp_attempts or 0) + 1
        cust.save(update_fields=["phone_otp_attempts"])
        return Response({"detail": "Código inválido ou expirado."}, status=status.HTTP_400_BAD_REQUEST)

    if not cust.is_phone_verified:
        cust.is_phone_verified = True
        cust.save(update_fields=["is_phone_verified"])

    return Response({"ok": True, "is_phone_verified": True})


@api_view(["GET"])
def customer_detail(request, pk: int):
    """
    Retorna dados básicos do cliente por ID.
    """
    try:
        cust = Customer.objects.get(pk=pk)
    except Customer.DoesNotExist:
        return Response({"detail": "Cliente não encontrado."}, status=status.HTTP_404_NOT_FOUND)

    payload = {
        "id": cust.id,
        "name": cust.name,
        "email": cust.email,
        "phone": cust.phone,
        "is_email_verified": cust.is_email_verified,
        "is_phone_verified": cust.is_phone_verified,
        "created_at": cust.created_at,
        "updated_at": cust.updated_at,
    }
    return Response(payload)



