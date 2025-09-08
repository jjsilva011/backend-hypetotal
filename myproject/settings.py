# myproject/settings.py — Perfil prod/dev consolidado (MEDIA habilitado)
import os
from pathlib import Path
import dj_database_url
from dotenv import load_dotenv

# -------------------------
# .env opcional (instance/.env)
# -------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / "instance" / ".env"
if ENV_PATH.exists():
    load_dotenv(ENV_PATH)

# -------------------------
# Segurança / modo
# -------------------------
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "django-insecure-fallback-key-for-dev")
DEBUG = os.getenv("DEBUG", "False").lower() == "true"

# Hosts permitidos (dev + produção)
ALLOWED_HOSTS: list[str] = [
    "127.0.0.1",
    "localhost",
    "hypetotal.com",
    "www.hypetotal.com",
    "api.hypetotal.com",
]
RENDER_EXTERNAL_HOSTNAME = os.getenv("RENDER_EXTERNAL_HOSTNAME")
if RENDER_EXTERNAL_HOSTNAME:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)

# -------------------------
# Apps
# -------------------------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    # Desativa o staticfiles embutido do runserver para o WhiteNoise assumir no dev
    "whitenoise.runserver_nostatic",
    "django.contrib.staticfiles",

    # terceiros
    "rest_framework",
    "django_filters",
    "corsheaders",

    # app local (usa AppConfig para carregar signals.py)
    "api.apps.ApiConfig",
]

# -------------------------
# Middlewares
# -------------------------
MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",          # antes de CommonMiddleware
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",     # WhiteNoise logo após Security
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "myproject.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        # Necessário para localizar templates de emails (templates/emails/*)
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "myproject.wsgi.application"

# -------------------------
# Banco de dados (prod/dev)
# -------------------------
DATABASES = {
    "default": dj_database_url.config(
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
        conn_max_age=600,
        ssl_require=bool(os.getenv("RENDER", "")),
    )
}

# -------------------------
# Validações de senha (padrão)
# -------------------------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# -------------------------
# Locale / Fuso horário
# -------------------------
LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Sao_Paulo"
USE_I18N = True
USE_TZ = True

# -------------------------
# Arquivos estáticos e mídia
# -------------------------
STATIC_URL = "/static/"
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")
# Em produção use Manifest (compress + hash). Em dev, deixe default.
if not DEBUG:
    STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# >>> MEDIA (upload local de imagens)
MEDIA_URL = "/media/"
MEDIA_ROOT = os.path.join(BASE_DIR, "media")
# <<<

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# -------------------------
# DRF (paginação + filtros/busca/ordenação)
# -------------------------
REST_FRAMEWORK = {
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
}

# -------------------------
# CORS / CSRF
# -------------------------

def _env_list(var_name: str, fallback: list[str]) -> list[str]:
    raw = os.getenv(var_name, "")
    if raw.strip():
        return [u.strip() for u in raw.split(",") if u.strip()]
    return fallback

# Fallbacks de DEV com várias portas (quando Vite troca a porta)
_DEV_ORIGINS = [
    "http://localhost:5173", "http://127.0.0.1:5173",
    "http://localhost:5175", "http://127.0.0.1:5175",
    "http://localhost:5176", "http://127.0.0.1:5176",
    "http://localhost:5177", "http://127.0.0.1:5177",
    "http://localhost:5178", "http://127.0.0.1:5178",
    "http://localhost:5179", "http://127.0.0.1:5179",
    "http://localhost:5180", "http://127.0.0.1:5180",
]
_PROD_ORIGINS = [
    "https://hypetotal.com",
    "https://www.hypetotal.com",
    "https://api.hypetotal.com",
]

CORS_ALLOWED_ORIGINS = _env_list("CORS_ALLOWED_ORIGINS", _PROD_ORIGINS + _DEV_ORIGINS)
CSRF_TRUSTED_ORIGINS = _env_list("CSRF_TRUSTED_ORIGINS", _PROD_ORIGINS + _DEV_ORIGINS)
CORS_ALLOW_CREDENTIALS = True  # necessário para enviar cookies de sessão/CSRF

# -------------------------
# Segurança (produção)
# -------------------------
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    # SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"

# -------------------------
# E-mail (ENV)
# -------------------------
EMAIL_BACKEND = os.getenv("EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = os.getenv("EMAIL_HOST", "localhost")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "25"))
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_SSL = os.getenv("EMAIL_USE_SSL", "False").lower() == "true"
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "False").lower() == "true"
EMAIL_TIMEOUT = int(os.getenv("EMAIL_TIMEOUT", "30"))
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "no-reply@hypetotal.com")

_notify = os.getenv("NOTIFY_NEW_ORDER_TO", "")
NOTIFY_NEW_ORDER_TO = [e.strip() for e in _notify.split(",") if e.strip()]














