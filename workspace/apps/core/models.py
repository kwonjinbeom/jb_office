from django.db import models


class AppSetting(models.Model):
    """화면에서 바꾸는 설정값. (.env 를 서버 콘솔에서 고치지 않아도 되게 하기 위한 것)"""

    key = models.CharField("키", max_length=60, unique=True)
    value = models.TextField("값", blank=True)
    updated_at = models.DateTimeField("수정", auto_now=True)

    class Meta:
        verbose_name = "앱 설정"
        verbose_name_plural = "앱 설정"

    def __str__(self) -> str:
        return self.key

    @classmethod
    def get(cls, key: str, default: str = "") -> str:
        row = cls.objects.filter(key=key).only("value").first()
        return row.value if row else default

    @classmethod
    def set(cls, key: str, value: str) -> None:
        cls.objects.update_or_create(key=key, defaults={"value": value})


WEBHOOK_SECRET_KEY = "deploy_webhook_secret"
