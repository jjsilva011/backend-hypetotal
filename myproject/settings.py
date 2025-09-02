# acrescente no topo:
import os

# substitua as duas linhas atuais por envs (opcional, mas recomendado):
SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-prod")
DEBUG = os.getenv("DEBUG", "true").lower() == "true"

# CORS (mantenha apenas seu domínio)
CORS_ALLOWED_ORIGINS = [
    "https://hypetotal.com",
    "https://www.hypetotal.com",
]

# Paginação default (opcional; usamos paginação por view mesmo)
REST_FRAMEWORK = {
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 10,
}

# Flag para permitir SEED em prod quando necessário
ENABLE_SEED = os.getenv("ENABLE_SEED", "false").lower() == "true"



