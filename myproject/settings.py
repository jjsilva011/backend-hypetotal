from pathlib import Path
import os

# -------------------------
# .env opcional (instance/.env)
# -------------------------
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / "instance" / ".env"
if ENV_PATH.exists():
    load_dotenv(ENV_PATH)

# -------------------------
# Segurança / modo
# -------------------------
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "change-me-in-prod")
DEBUG = os.getenv("DEBUG", "False").lower() == "true"

def csv_env(name: str, default: str = "") -> list[str]:
    """
    Lê uma variável de ambiente como CSV e devolve lista limpa.
    Ex.: "a,b, c " -> ["a","b","c"]
    """
    raw = os.getenv(name, default)
    return [x.strip() for x in raw.split(",") if x.strip()]

ALLOWED_HOSTS = csv_env(
    "ALLOWED_HOSTS",
    "127.0.0.1,localhost,api.hypetotal.com,www.hypetotal.com,staging.hypetotal.com"
)

# -------------------------
# Apps
# -------------------------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # terceiros
    "rest_framework",
    "django_filters",
    "corsheaders",

    # app local
    "api",
]

# -------------------------
# Middlewares
# -------------------------
MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",  # antes do CommonMiddleware
    "django.middleware.security.SecurityMiddleware",
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
        "DIRS": [],
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
ASGI_APPLICATION = "myproject.asgi.application"

# -------------------------
# Banco de dados (robusto)
# -------------------------
DB_URL = os.getenv("DATABASE_URL", "").strip()
try:
    from dj_database_url import parse as dburl  # type: ignore
except Exception:
    dburl = None

if DB_URL and dburl:
    DATABASES = {
        "default": dburl(
            DB_URL,
            conn_max_age=600,
            ssl_require=os.getenv("REQUIRE_DB_SSL", "1") == "1",
        )
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": str(BASE_DIR / "db.sqlite3"),
        }
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
# Arquivos estáticos
# -------------------------
STATIC_URL = "/static/"
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# -------------------------
# Conveniência
# -------------------------
APPEND_SLASH = True

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
# (⚠️ csv_env já foi definido acima; não mover este bloco para cima)
# -------------------------
CORS_ALLOWED_ORIGINS = csv_env(
    "CORS_ALLOWED_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173,https://hypetotal.com,https://www.hypetotal.com"
)

CSRF_TRUSTED_ORIGINS = csv_env(
    "CSRF_TRUSTED_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173,https://hypetotal.com,https://www.hypetotal.com"
)

CORS_ALLOW_CREDENTIALS = True

# Aceita qualquer porta de localhost/127.0.0.1 (Vite pode usar 5173/5174/5175…)
CORS_ALLOWED_ORIGIN_REGEXES = [
    r"^http://localhost:\d+$",
    r"^http://127\.0\.0\.1:\d+$",
]

# -------------------------
# Segurança (produção)
# -------------------------
SECURE_SSL_REDIRECT = not DEBUG
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SECURE_HSTS_SECONDS = 0 if DEBUG else 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = not DEBUG
SECURE_HSTS_PRELOAD = not DEBUG
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
X_FRAME_OPTIONS = "SAMEORIGIN"
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# -------------------------
# Flag operacional para seed
# -------------------------
ENABLE_SEED = os.getenv("ENABLE_SEED", "false").lower() == "true"

# -------------------------
# Logging simples
# -------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "INFO"},
}











