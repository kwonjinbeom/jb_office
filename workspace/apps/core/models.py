from django.db import models


class LiveQuerySet(models.QuerySet):
    def delete(self):
        from .trash import move_queryset
        return move_queryset(self)


class LiveManager(models.Manager.from_queryset(LiveQuerySet)):
    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)


class TrashableModel(models.Model):
    """본문을 복제하지 않는 공통 삭제 표시. 기본 조회에서는 휴지통 항목을 제외한다."""
    deleted_at = models.DateTimeField("삭제 시각", null=True, blank=True, db_index=True, editable=False)
    objects = LiveManager()
    all_objects = models.Manager()

    class Meta:
        abstract = True

    def delete(self, using=None, keep_parents=False):
        from .trash import move_to_trash
        entry = move_to_trash(self)
        return (1, {self._meta.label: 1}) if entry else (0, {})

    def validate_unique(self, exclude=None):
        from django.core.exceptions import ValidationError
        super().validate_unique(exclude=exclude)
        errors = {}
        for field in self._meta.fields:
            if field.primary_key or not field.unique or field.name in (exclude or []):
                continue
            value = getattr(self, field.attname)
            if value is not None and type(self).all_objects.filter(deleted_at__isnull=False, **{field.attname: value}).exclude(pk=self.pk).exists():
                errors[field.name] = "휴지통에 같은 값이 있습니다. 기존 항목을 복원하거나 다른 값을 사용하세요."
        if errors:
            raise ValidationError(errors)


class TrashEntry(models.Model):
    model_label = models.CharField(max_length=80)
    object_key = models.CharField(max_length=512)
    title = models.CharField("이름", max_length=200)
    section = models.CharField("원래 위치", max_length=80)
    deleted_at = models.DateTimeField("삭제한 때", db_index=True)
    # 모델명과 PK 목록만 저장한다. 본문·이미지·버전 내용은 복제하지 않는다.
    members = models.JSONField(default=dict)

    class Meta:
        ordering = ["-deleted_at", "-pk"]
        constraints = [models.UniqueConstraint(fields=["model_label", "object_key"], name="unique_trash_object")]

    @property
    def expires_at(self):
        from datetime import timedelta
        return self.deleted_at + timedelta(days=7)

    @property
    def item_count(self):
        return sum(len(ids) for ids in self.members.values()) or 1


class SourceExclusion(models.Model):
    """읽기 전용 Git 자료의 화면 제외 키. 만료 후에도 원본 재수입을 막는다."""
    kind = models.CharField(max_length=24)
    key = models.CharField(max_length=512)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["kind", "key"], name="unique_source_exclusion")]


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
