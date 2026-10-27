"""블로그·카페 › 운영: 블로그별 발행 계획(할 일)과 실제 발행 기록, 주간 현황.

- Plan: 언제 어느 블로그에 무엇을 올릴지. 상태 원고 → 손질 → 예약 → 발행.
- FeedEntry / FeedState: 블로그 RSS 에서 읽은 실제 발행 글과 마지막으로 읽은 결과.
  서버(PythonAnywhere 무료 계정)는 티스토리·네이버 주소에 나갈 수 없을 수 있다. 그때는 Plan 의 '발행' 기록으로 센다.
블로그 목록은 운영 화면의 Blog (apps.blog_rules) 를 쓴다.
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
    # 통계 수집 (방문자 · 공감 · 댓글): RSS 와 같은 PC 실행에서 같이 읽는다 (stats.collect)
    stat_checked_at = models.DateTimeField(null=True, blank=True)
    stat_ok = models.BooleanField(default=False)
    stat_message = models.CharField(max_length=200, blank=True)
    # GA4 (2026-10-27): 같은 PC 실행에서 받는다 (routines.site_views.collect). 유입은 최근 30일 [[경로, 세션]]
    ga_checked_at = models.DateTimeField(null=True, blank=True)
    ga_channels = models.JSONField(default=list, blank=True)


class SiteStat(models.Model):
    """통계현황 (2026-10-23 사용자): 사이트별 하루 방문자 · 공감 · 댓글.
    자동 수집(stats.collect)이 채우고, 화면에서 직접 넣을 수도 있다 (hand=True 인 날은 자동이 덮어쓰지 않는다).
    likes_total · comments_total 은 자동 수집이 본 최근 글들의 공감·댓글 합계 — 전날 합계와의 차이가 그날 공감·댓글이다."""
    blog = models.ForeignKey(Blog, on_delete=models.CASCADE, related_name="stats")
    day = models.DateField("날짜")
    visitors = models.PositiveIntegerField("방문자", null=True, blank=True)
    likes = models.PositiveIntegerField("공감", null=True, blank=True)
    comments = models.PositiveIntegerField("댓글", null=True, blank=True)
    likes_total = models.PositiveIntegerField(null=True, blank=True)
    comments_total = models.PositiveIntegerField(null=True, blank=True)
    visitors_total = models.PositiveIntegerField(null=True, blank=True)  # 그날 마지막 수집 때 누적 방문자 (다음 날 어제를 마저 채운다)
    views = models.PositiveIntegerField("조회수", null=True, blank=True)  # GA4 가 채운 날: 방문자도 GA4 사용자 수 (공개 숫자가 덮지 않는다)
    hand = models.BooleanField("직접 넣음", default=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["day"]
        constraints = [models.UniqueConstraint(fields=["blog", "day"], name="blog_ops_sitestat_unique")]

    def __str__(self):
        return f"{self.blog} {self.day}"


class SitePage(models.Model):
    """통계현황 '많이 본 글' (2026-10-27 사용자): GA4 최근 30일 글별 조회수. 수집 때마다 사이트 것을 통째로 바꾼다."""
    blog = models.ForeignKey(Blog, on_delete=models.CASCADE, related_name="pages")
    path = models.CharField(max_length=500)
    title = models.CharField(max_length=300, blank=True)
    views = models.PositiveIntegerField(default=0)
    users = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-views"]

    def __str__(self):
        return f"{self.blog} {self.path}"
