"""블로그·카페 › 규칙: 어떤 블로그에서 무엇을 하루 몇 편 쓰는지, 매일 지킬 규칙.

처음 값과 근거: 콘텐츠/블로그_카페/포스팅자동화/10_플랫폼별_자동화_위험.md, 11_운영계획_검증.md (2026-10-16 사용자 확정).
"""
from django.db import models

from apps.core.models import TrashableModel


class Blog(TrashableModel):
    class Platform(models.TextChoices):
        TISTORY = "tistory", "티스토리"
        NAVER = "naver", "네이버"
        BLOGGER = "blogger", "블로거"
        WORDPRESS = "wordpress", "워드프레스"

    class Status(models.TextChoices):
        ACTIVE = "active", "운영"
        READY = "ready", "준비"
        HOLD = "hold", "보류"

    name = models.CharField("블로그", max_length=40)
    platform = models.CharField("플랫폼", max_length=12, choices=Platform.choices)
    status = models.CharField("상태", max_length=8, choices=Status.choices, default=Status.ACTIVE)
    address = models.URLField("주소", max_length=300, blank=True)
    account = models.CharField("계정", max_length=60, blank=True,
                               help_text="같은 계정이면 하루 편수를 합쳐서 본다 (예: 카카오 계정 1)")
    revenue = models.CharField("수익", max_length=60, blank=True, help_text="예: 애드센스, 방문자 + 쇼핑커넥트(간혹)")
    daily = models.PositiveSmallIntegerField("하루 편수", default=1)
    daily_note = models.CharField("편수 메모", max_length=80, blank=True, help_text="예: 애드센스 승인 뒤 2편")
    content = models.CharField("쓰는 글", max_length=200, blank=True)
    kpi = models.CharField("지표", max_length=80, blank=True)
    note = models.TextField("메모", blank=True)
    order = models.PositiveIntegerField("순서", default=0)

    class Meta:
        ordering = ["order", "pk"]

    def __str__(self):
        return self.name


class Rule(TrashableModel):
    class Group(models.TextChoices):
        COMMON = "common", "공통"
        CHECK = "check", "발행 전 손질"
        NAVER = "naver", "네이버"
        TISTORY = "tistory", "티스토리·구글"
        BAN = "ban", "금지"

    group = models.CharField("묶음", max_length=10, choices=Group.choices)
    body = models.CharField("규칙", max_length=200)
    note = models.CharField("근거·메모", max_length=200, blank=True)
    order = models.PositiveIntegerField("순서", default=0)

    class Meta:
        ordering = ["order", "pk"]

    def __str__(self):
        return self.body
