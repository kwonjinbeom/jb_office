"""블로그·카페 › 규칙: 사이트(블로그)마다 컨셉·하루 편수·수익·지표와, 그 사이트에서 까먹지 말고 체크할 것.

일반 규칙(누구나 아는 것)은 두지 않는다 (2026-10-16 사용자). 체크(Rule)는 사이트에 붙는다.

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
    content = models.CharField("컨셉", max_length=200, blank=True)
    routine = models.BooleanField("글쓰기 루틴", default=True,
                                  help_text="일일루틴 글쓰기가 이 사이트 원고를 쓴다 (끄면 사용자가 직접 쓰는 사이트)")
    kpi = models.CharField("지표", max_length=80, blank=True)
    note = models.TextField("메모", blank=True)
    order = models.PositiveIntegerField("순서", default=0)

    class Meta:
        ordering = ["order", "pk"]

    def __str__(self):
        return self.name

    @property
    def sel(self):
        """글 관리 화면의 사이트 카테고리 트리에서 고를 때 쓰는 값"""
        return f"b{self.pk}"


class Rule(TrashableModel):
    """사이트에서 까먹지 말고 체크할 것 한 줄. group 은 예전 일반 규칙 묶음이라 화면에서 쓰지 않는다."""

    class Group(models.TextChoices):
        COMMON = "common", "공통"
        CHECK = "check", "발행 전 손질"
        NAVER = "naver", "네이버"
        TISTORY = "tistory", "티스토리·구글"
        BAN = "ban", "금지"

    blog = models.ForeignKey(Blog, verbose_name="사이트", on_delete=models.CASCADE, related_name="checks",
                             null=True, blank=True)
    group = models.CharField("묶음", max_length=10, choices=Group.choices, default=Group.COMMON)
    body = models.CharField("체크", max_length=200)
    note = models.CharField("근거·메모", max_length=200, blank=True)
    order = models.PositiveIntegerField("순서", default=0)

    class Meta:
        ordering = ["order", "pk"]

    def __str__(self):
        return self.body


class SiteDay(models.Model):
    """운영 화면에서 고친 그날 숫자. 비어 있으면(None) 자동으로 센 값을 쓴다."""

    blog = models.ForeignKey(Blog, verbose_name="사이트", on_delete=models.CASCADE, related_name="days")
    day = models.DateField("날짜")
    published = models.PositiveSmallIntegerField("발행", null=True, blank=True)
    drafts = models.PositiveSmallIntegerField("임시저장", null=True, blank=True)

    class Meta:
        verbose_name = "사이트 날짜별 숫자"
        verbose_name_plural = verbose_name
        constraints = [models.UniqueConstraint(fields=["blog", "day"], name="blog_rules_siteday_unique")]

    def __str__(self):
        return f"{self.blog} {self.day}"
