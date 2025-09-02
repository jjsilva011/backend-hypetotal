from pathlib import Path
import os
import dj_database_url  # <- para parsear DATABASE_URL

BASE_DIR = Path(__file__).resolve().parent.parent

# Segurança / modo
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "change-me-in-prod")
DEBUG = os.getenv("DEBUG", "False").lower() == "true"

ALLOWED_HOSTS = [
    "127.0.0.1",
    "localhost",
    "api.hypetotal.com",
]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # terceiros
    "rest_framework",
    "corsheaders",
    # app local
    "api",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",  # <- acima de CommonMiddleware
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

# -----------------------------
# Banco de dados (Render/Local)
# -----------------------------
# Se houver DATABASE_URL (ex.: postgres://...) use Postgres.
# Caso contrário, caia para SQLite local.
DEFAULT_SQLITE_URL = f"sqlite:///{BASE_DIR / 'db.sqlite3'}"
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()

if DATABASE_URL:
    # Parseia a URL do Render em dict Django
    DATABASES = {
        "default": dj_database_url.parse(
            DATABASE_URL,
            conn_max_age=600,
            ssl_require=os.getenv("REQUIRE_DB_SSL", "1") == "1",
        )
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

# Validações de senha (padrão)
AUTH_PASSWORD_VALIDATORS = [
    {"name": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"name": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"name": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"name": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Conveniência
APPEND_SLASH = True

# CORS
CORS_ALLOWED_ORIGINS = [
    "https://hypetotal.com",
]

# DRF: paginação (backup global)
REST_FRAMEWORK = {
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 10,
}

# Libera seed em ambiente controlado (opcional)
ENABLE_SEED = os.getenv("ENABLE_SEED", "false").lower() == "true"





