from urllib.parse import urlparse

from django.db import models
from django.urls import reverse


class Evidence(models.Model):
    """조사 중 발견한 링크 하나. 어느 아이디어·실험의 근거인지 연결한다."""

    class Kind(models.TextChoices):
        JOB = "job", "의뢰 공고"
        REVIEW = "review", "리뷰·불만"
        PRICE = "price", "가격·판매"
        POLICY = "policy", "정책·수수료"
        STAT = "stat", "통계·지표"
        COMPETITOR = "competitor", "경쟁 제품"
        OTHER = "other", "기타"

    url = models.URLField("URL", max_length=600)
    title = models.CharField("제목", max_length=200, blank=True, help_text="비우면 주소의 도메인으로 표시")
    kind = models.CharField("유형", max_length=20, choices=Kind.choices, default=Kind.OTHER)
    note = models.TextField("한 줄 메모", blank=True, help_text="무엇을 증명하는지. 숫자가 있으면 숫자를 적는다")
    idea = models.ForeignKey(
        "ideas.Idea", verbose_name="아이디어", null=True, blank=True, on_delete=models.SET_NULL, related_name="links"
    )
    stage = models.ForeignKey(
        "ideas.Stage", verbose_name="단계", null=True, blank=True, on_delete=models.SET_NULL, related_name="links"
    )
    captured_at = models.DateTimeField("수집", auto_now_add=True)
    updated_at = models.DateTimeField("수정", auto_now=True)

    class Meta:
        ordering = ["-captured_at"]
        verbose_name = "증거"
        verbose_name_plural = "증거"

    def __str__(self) -> str:
        return self.display_title

    def get_absolute_url(self) -> str:
        return reverse("evidence:edit", args=[self.pk])

    @property
    def domain(self) -> str:
        try:
            host = urlparse(self.url).netloc
        except ValueError:
            return ""
        return host[4:] if host.startswith("www.") else host

    @property
    def display_title(self) -> str:
        return self.title or self.domain or self.url
