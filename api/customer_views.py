# api/customer_views.py — registro e verificação (e-mail/telefone) robustos
from __future__ import annotations

import secrets
import random
from datetime import timedelta

from django.conf import settings
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.template import TemplateDoesNotExist
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status

from django.core.mail import EmailMultiAlternatives, get_connection

from .models import Customer
from .customer_serializers import CustomerSerializer


# ---------------------------
# Helpers
# ---------------------------
def _gen_email_token() -> str:
    return secrets.token_urlsafe(24)

def _gen_otp() -> str:
    return f"{random.randint(0, 999999):06d}"

def _public_front_base() -> str:
    # Ajuste para o seu domínio público quando desejar (ex.: https://www.hypetotal.com)
    return getattr(settings, "PUBLIC_FRONT_BASE", "").rstrip("/") or "http://127.0.0.1:5178"

def _public_api_base() -> str:
    # Em produção, configure PUBLIC_API_BASE="https://api.hypetotal.com/api"
    return getattr(settings, "PUBLIC_API_BASE", "").rstrip("/") or "http://127.0.0.1:8000/api"


def _send_verification_email(customer: Customer) -> bool:
    """
    Envia e-mail de verificação. Nunca deixa a view quebrar:
    - Se faltar template, usa fallback em texto puro.
    - Se backend SMTP falhar, devolve False (caller decide o que fazer).
    """
    token = customer.email_verification_token
    cid = customer.id

    front_link = f"{_public_front_base()}/verify-email?cid={cid}&token={token}"
    api_link = f"{_public_api_base()}/customers/verify-email/?customer_id={cid}&token={token}"

    ctx = {
        "customer": customer,
        "front_verify_url": front_link,
        "api_verify_url": api_link,
    }

    subject = "[HypeTotal] Confirme seu e-mail"
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@hypetotal.com")
    to = [customer.email]

    # Tenta renderizar HTML/TXT — com fallback seguro
    try:
        html = render_to_string("emails/verify_email.html", ctx)
    except TemplateDoesNotExist:
        html = f"<p>Olá {customer.name},</p><p>Confirme seu e-mail:<br><a href='{front_link}'>{front_link}</a></p><p>Ou backend: {api_link}</p>"

    try:
        txt = render_to_string("emails/verify_email.txt", ctx)
    except TemplateDoesNotExist:
        txt = f"Olá {customer.name},\n\nConfirme seu e-mail:\n{front_link}\n(backend: {api_link})\n"

    try:
        # Abre conexão explícita (alguns backends exigem)
        with get_connection() as conn:
            msg = EmailMultiAlternatives(subject, txt, from_email, to, connection=conn)
            msg.attach_alternative(html, "text/html")
            msg.send(fail_silently=False)
        return True
    except Exception:
        return False


# ---------------------------
# Views
# ---------------------------
@csrf_exempt
@api_view(["POST"])
@permission_classes([AllowAny])
def register_customer(request):
    """
    Cria/atualiza um cliente e dispara verificações:
    - E-mail: link com token
    - Telefone: OTP de 6 dígitos (expira em 10min)
    Payload: { "name": "...", "email": "...", "phone": "+55..." }
    Em DEBUG, retornamos token/otp no payload para facilitar testes.
    """
    data = request.data or {}
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    phone = (data.get("phone") or "").strip()

    if not name or not email:
        return Response({"detail": "Campos obrigatórios: name, email."}, status=400)

    customer, created = Customer.objects.get_or_create(
        email=email,
        defaults={"name": name, "phone": phone}
    )

    if not created:
        changed = False
        if name and customer.name != name:
            customer.name = name; changed = True
        if phone and customer.phone != phone:
            customer.phone = phone; changed = True
        if changed:
            customer.save(update_fields=["name", "phone"])

    # Gera token e OTP
    customer.email_verification_token = _gen_email_token()
    customer.email_token_created_at = timezone.now()

    if phone:
        customer.phone_otp_code = _gen_otp()
        customer.phone_otp_expires_at = timezone.now() + timedelta(minutes=10)
        customer.phone_otp_attempts = 0
    else:
        customer.phone_otp_code = ""
        customer.phone_otp_expires_at = None
        customer.phone_otp_attempts = 0

    customer.save()

    email_sent = _send_verification_email(customer)

    resp = {
        "ok": True,
        "customer": CustomerSerializer(customer).data,
        "email_sent": email_sent,
        "phone_otp_sent": bool(customer.phone_otp_code),
    }
    if settings.DEBUG:
        resp["debug"] = {
            "email_token": customer.email_verification_token,
            "phone_otp": customer.phone_otp_code,
        }
    return Response(resp, status=201 if created else 200)


@csrf_exempt
@api_view(["GET", "POST"])
@permission_classes([AllowAny])
def verify_email(request):
    """
    Confirma e-mail por GET (link) ou POST (JSON).
    GET  ?customer_id=..&token=..
    POST { "customer_id": 1, "token": "..." }
    """
    if request.method == "GET":
        customer_id = request.GET.get("customer_id")
        token = request.GET.get("token")
    else:
        customer_id = (request.data or {}).get("customer_id")
        token = (request.data or {}).get("token")

    try:
        customer = Customer.objects.get(id=int(customer_id))
    except Exception:
        return Response({"ok": False, "detail": "Cliente não encontrado."}, status=404)

    if not token or not customer.email_token_is_valid(str(token)):
        return Response({"ok": False, "detail": "Token inválido."}, status=400)

    customer.is_email_verified = True
    customer.email_verification_token = ""
    customer.email_token_created_at = None
    customer.save(update_fields=["is_email_verified", "email_verification_token", "email_token_created_at"])

    if request.method == "GET":
        return HttpResponse("<h1>E-mail verificado com sucesso.</h1>", content_type="text/html")

    return Response({"ok": True, "customer": CustomerSerializer(customer).data})


@csrf_exempt
@api_view(["POST"])
@permission_classes([AllowAny])
def verify_phone(request):
    """
    Confirma telefone via OTP.
    Body: { "customer_id": 1, "otp": "123456" }
    """
    data = request.data or {}
    customer_id = data.get("customer_id")
    otp = (data.get("otp") or "").strip()

    try:
        customer = Customer.objects.get(id=int(customer_id))
    except Exception:
        return Response({"ok": False, "detail": "Cliente não encontrado."}, status=404)

    # Limite simples
    if (customer.phone_otp_attempts or 0) >= 5:
        return Response({"ok": False, "detail": "Muitas tentativas. Solicite novo código."}, status=429)

    if not customer.phone_otp_is_valid(otp):
        customer.phone_otp_attempts = (customer.phone_otp_attempts or 0) + 1
        customer.save(update_fields=["phone_otp_attempts"])
        return Response({"ok": False, "detail": "OTP inválido ou expirado."}, status=400)

    customer.is_phone_verified = True
    customer.phone_otp_code = ""
    customer.phone_otp_expires_at = None
    customer.phone_otp_attempts = 0
    customer.save(update_fields=["is_phone_verified", "phone_otp_code", "phone_otp_expires_at", "phone_otp_attempts"])

    return Response({"ok": True, "customer": CustomerSerializer(customer).data})


@api_view(["GET"])
@permission_classes([AllowAny])
def customer_detail(request, pk: int):
    try:
        c = Customer.objects.get(id=int(pk))
    except Exception:
        return Response({"detail": "Cliente não encontrado."}, status=404)
    return Response(CustomerSerializer(c).data, status=200)

