from django.db import models
from django.utils import timezone

from .standard import FIELDS


class SearchStandard(models.Model):
    """아이디어 검색 표준의 한 버전. 저장할 때마다 새 줄이 생기고, version 이 가장 큰 것이 현재 표준이다."""

    version = models.PositiveIntegerField("버전", unique=True)
    goal = models.TextField("목적과 방향", blank=True)
    approach = models.TextField("조사 방식", blank=True)
    profile = models.TextField("나의 조건과 자산", blank=True)
    areas = models.TextField("찾을 분야와 비중", blank=True)
    criteria = models.TextField("좋은 아이디어의 기준", blank=True)
    exclude = models.TextField("제외할 것", blank=True)
    evidence_rules = models.TextField("근거와 출처 규칙", blank=True)
    output = models.TextField("결과에 담을 것", blank=True)
    focus = models.TextField("이번에 특히 볼 것", blank=True)
    note = models.CharField("바꾼 점", max_length=140, blank=True, help_text="무엇을 왜 바꿨는지 한 줄. 버전 기록에 남습니다.")
    created_at = models.DateTimeField("저장한 때", auto_now_add=True)

    class Meta:
        ordering = ["-version"]
        verbose_name = "아이디어 검색 표준"
        verbose_name_plural = "아이디어 검색 표준"

    def __str__(self) -> str:
        return f"v{self.version}"

    @classmethod
    def latest(cls) -> "SearchStandard | None":
        return cls.objects.order_by("-version").first()

    def values(self) -> dict[str, str]:
        return {name: getattr(self, name) for name in FIELDS}

    def same_as(self, values: dict[str, str]) -> bool:
        return all((getattr(self, name) or "").strip() == (values.get(name) or "").strip() for name in FIELDS)

    @property
    def saved_label(self) -> str:
        return timezone.localtime(self.created_at).strftime("%Y-%m-%d %H:%M") if self.created_at else ""
