from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'openlxp_xia'

    def ready(self):
        import openlxp_xia.signals  # noqa
