from pathlib import Path
import os

# ===== Paths base =====
BASE_DIR = Path(__file__).resolve().parent.parent

# ===== Segurança / Debug =====
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "change-me-in-prod")
DEBUG = os.getenv("DJANGO_DEBUG", "False").lower() in ("1", "true", "yes")

# Hosts permitidos (dev + Render + seu domínio)
ALLOWED_HOSTS = [
    "127.0.0.1",
    "localhost",
    "api.hypetotal.com",
    ".onrender.com",  # domínio interno do Render
]

# ===== Apps =====
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Terceiros
    "rest_framework",
    "corsheaders",
    # App local
    "api",
]

# ===== Middleware =====
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",   # <- precisa vir antes do CommonMiddleware
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
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "myproject.wsgi.application"

# ===== Banco de dados =====
# Mantemos SQLite por padrão. Se algum dia você definir DATABASE_URL,
# troque aqui para Postgres com dj-database-url (quando adicionar a dependência).
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# ===== Validações de senha =====
AUTH_PASSWORD_VALIDATORS = [
    {"name": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"name": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"name": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"name": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ===== Localização =====
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# ===== Arquivos estáticos (admin etc.) =====
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ===== Conveniências =====
APPEND_SLASH = True

# ===== CORS / CSRF =====
# Origem do frontend em produção (site)
CORS_ALLOWED_ORIGINS = [
    "https://hypetotal.com",
    "https://www.hypetotal.com",
]
# Facilitar o desenvolvimento local (Vite/React, se usar)
if DEBUG:
    CORS_ALLOWED_ORIGINS += [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

# Se algum endpoint usar sessão/cookie, liste os domínios confiáveis de CSRF
CSRF_TRUSTED_ORIGINS = [
    "https://hypetotal.com",
    "https://www.hypetotal.com",
    "https://*.onrender.com",
]

# Quando atrás de proxy (Render/Cloudflare) para detecção correta de HTTPS
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

