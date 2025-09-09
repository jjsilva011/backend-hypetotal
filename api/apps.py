from django.apps import AppConfig


class ApiConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "api"
    verbose_name = "HypeTotal API"

    def ready(self):
        # Carrega sinais se existirem, mas não falha se não houver no deploy
        try:
            from . import signals  # noqa: F401
        except Exception:
            pass


