"""블로그·카페 › 운영: 블로그별 발행 계획(할 일)과 실제 발행 기록, 주간 현황.

- Plan: 언제 어느 블로그에 무엇을 올릴지. 상태 원고 → 손질 → 예약 → 발행.
- FeedEntry / FeedState: 블로그 RSS 에서 읽은 실제 발행 글과 마지막으로 읽은 결과.
  서버(PythonAnywhere 무료 계정)는 티스토리·네이버 주소에 나갈 수 없을 수 있다. 그때는 Plan 의 '발행' 기록으로 센다.
블로그 목록은 규칙 화면의 Blog (apps.blog_rules) 를 쓴다.
"""
from django.db import models

from apps.blog_rules.models import Blog
from apps.core.models import TrashableModel


class Plan(TrashableModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "원고"
        EDIT = "edit", "손질"
        SCHEDULED = "scheduled", "예약"
        PUBLISHED = "published", "발행"

    blog = models.ForeignKey(Blog, verbose_name="블로그", on_delete=models.CASCADE, related_name="plans")
    planned_on = models.DateField("발행 예정일")
    title = models.CharField("제목", max_length=200)
    status = models.CharField("상태", max_length=10, choices=Status.choices, default=Status.DRAFT)
    url = models.URLField("발행 주소", max_length=500, blank=True)
    published_on = models.DateField("발행일", null=True, blank=True)
    memo = models.CharField("메모", max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["planned_on", "blog__order", "pk"]

    def __str__(self):
        return self.title


class FeedEntry(models.Model):
    blog = models.ForeignKey(Blog, on_delete=models.CASCADE, related_name="feed_entries")
    title = models.CharField(max_length=300)
    url = models.URLField(max_length=500, unique=True)
    published_at = models.DateTimeField()

    class Meta:
        ordering = ["-published_at"]


class FeedState(models.Model):
    blog = models.OneToOneField(Blog, on_delete=models.CASCADE, related_name="feed_state")
    feed_url = models.URLField(max_length=500, blank=True)
    checked_at = models.DateTimeField(null=True, blank=True)
    ok = models.BooleanField(default=False)
    message = models.CharField(max_length=200, blank=True)
