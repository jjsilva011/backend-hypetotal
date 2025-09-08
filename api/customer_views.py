# api/customer_views.py — registro e verificação (e-mail/telefone)
import secrets
import random
from datetime import timedelta

from django.conf import settings
from django.http import JsonResponse, HttpResponse
from django.template.loader import render_to_string
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework import status

from django.core.mail import EmailMultiAlternatives

from .models import Customer
from .customer_serializers import CustomerSerializer

# Helpers
def _gen_email_token() -> str:
    return secrets.token_urlsafe(24)

def _gen_otp() -> str:
    return f"{random.randint(0, 999999):06d}"

def _public_front_base() -> str:
    # Em DEV o front é vite (porta variável). Para o e-mail, use o domínio público quando tiver.
    # Aqui usamos o canônico de DEV para ilustrar a rota de confirmação de e-mail no front.
    # Ajuste se desejar: https://www.hypetotal.com
    return "http://127.0.0.1:5178"

def _public_api_base() -> str:
    return getattr(settings, "PUBLIC_API_BASE", "").rstrip("/") or "http://127.0.0.1:8000/api"


def _send_verification_email(customer: Customer):
    token = customer.email_verification_token
    cid = customer.id

    # Link para confirmar pelo FRONT (ideal para UX)
    front_link = f"{_public_front_base()}/verify-email?cid={cid}&token={token}"
    # Fallback direto no backend (útil em DEV)
    api_link = f"{_public_api_base()}/customers/verify-email/?customer_id={cid}&token={token}"

    ctx = {
        "customer": customer,
        "front_verify_url": front_link,
        "api_verify_url": api_link,
    }

    subject = "[HypeTotal] Confirme seu e-mail"
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@hypetotal.com")
    to = [customer.email]

    html = render_to_string("emails/verify_email.html", ctx)
    txt = render_to_string("emails/verify_email.txt", ctx)

    msg = EmailMultiAlternatives(subject, txt, from_email, to)
    msg.attach_alternative(html, "text/html")
    msg.send(fail_silently=False)


@csrf_exempt
@api_view(["POST"])
@permission_classes([AllowAny])
def register_customer(request):
    """
    Cria/atualiza um cliente e dispara verificação:
    - E-mail: link com token
    - Telefone: OTP de 6 dígitos (expira em 10min)
    Em DEBUG, retornamos token/otp no payload para facilitar teste.
    Payload esperado: { "name": "...", "email": "...", "phone": "+55..." }
    """
    name = (request.data.get("name") or "").strip()
    email = (request.data.get("email") or "").strip().lower()
    phone = (request.data.get("phone") or "").strip()

    if not name or not email:
        return JsonResponse({"detail": "Campos obrigatórios: name, email."}, status=400)

    customer, created = Customer.objects.get_or_create(email=email, defaults={"name": name, "phone": phone})
    if not created:
        # Atualiza nome/telefone se enviados
        if name:
            customer.name = name
        if phone:
            customer.phone = phone

    # Gera token de e-mail e OTP de telefone
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

    # Dispara e-mail (SMTP real já configurado)
    try:
        _send_verification_email(customer)
        email_sent = True
    except Exception as e:
        email_sent = False

    # Telefone: aqui você pode integrar WhatsApp/SMS (Twilio, TotalVoice, Zenvia etc.)
    # Em DEV, não enviamos nada externo. Retornamos o OTP se DEBUG==True.
    phone_otp_sent = bool(customer.phone_otp_code)

    resp = {
        "ok": True,
        "customer": CustomerSerializer(customer).data,
        "email_sent": email_sent,
        "phone_otp_sent": phone_otp_sent,
    }
    if settings.DEBUG:
        resp["debug"] = {
            "email_token": customer.email_verification_token,
            "phone_otp": customer.phone_otp_code,
        }
    return JsonResponse(resp, status=201)


@csrf_exempt
@api_view(["GET", "POST"])
@permission_classes([AllowAny])
def verify_email(request):
    """
    Confirma e-mail por GET (link no e-mail) ou POST (JSON).
    GET params: ?customer_id=..&token=..
    POST body: { "customer_id": 1, "token": "..." }
    """
    if request.method == "GET":
        customer_id = request.GET.get("customer_id")
        token = request.GET.get("token")
    else:
        customer_id = request.data.get("customer_id")
        token = request.data.get("token")

    try:
        customer = Customer.objects.get(id=int(customer_id))
    except Exception:
        return JsonResponse({"ok": False, "detail": "Cliente não encontrado."}, status=404)

    if not token or not customer.email_token_is_valid(token):
        return JsonResponse({"ok": False, "detail": "Token inválido."}, status=400)

    customer.is_email_verified = True
    customer.email_verification_token = ""
    customer.email_token_created_at = None
    customer.save(update_fields=["is_email_verified", "email_verification_token", "email_token_created_at"])

    # Se for GET (provindo do link do e-mail), devolve um HTML simples “verificado”
    if request.method == "GET":
        return HttpResponse("<h1>E-mail verificado com sucesso.</h1>", content_type="text/html")

    return JsonResponse({"ok": True, "customer": CustomerSerializer(customer).data})


@csrf_exempt
@api_view(["POST"])
@permission_classes([AllowAny])
def verify_phone(request):
    """
    Confirma telefone via OTP.
    Body: { "customer_id": 1, "otp": "123456" }
    """
    customer_id = request.data.get("customer_id")
    otp = (request.data.get("otp") or "").strip()

    try:
        customer = Customer.objects.get(id=int(customer_id))
    except Exception:
        return JsonResponse({"ok": False, "detail": "Cliente não encontrado."}, status=404)

    # Limite simples de tentativas
    if customer.phone_otp_attempts >= 5:
        return JsonResponse({"ok": False, "detail": "Muitas tentativas. Solicite novo código."}, status=429)

    if not customer.phone_otp_is_valid(otp):
        customer.phone_otp_attempts += 1
        customer.save(update_fields=["phone_otp_attempts"])
        return JsonResponse({"ok": False, "detail": "OTP inválido ou expirado."}, status=400)

    customer.is_phone_verified = True
    customer.phone_otp_code = ""
    customer.phone_otp_expires_at = None
    customer.phone_otp_attempts = 0
    customer.save(update_fields=["is_phone_verified", "phone_otp_code", "phone_otp_expires_at", "phone_otp_attempts"])

    return JsonResponse({"ok": True, "customer": CustomerSerializer(customer).data})


@api_view(["GET"])
@permission_classes([AllowAny])
def customer_detail(request, pk: int):
    try:
        c = Customer.objects.get(id=pk)
    except Exception:
        return JsonResponse({"detail": "Cliente não encontrado."}, status=404)
    return JsonResponse(CustomerSerializer(c).data, status=200)
