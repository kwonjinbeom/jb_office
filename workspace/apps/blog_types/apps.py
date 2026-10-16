from django.apps import AppConfig


class BlogTypesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.blog_types"
    verbose_name = "글 관리"
