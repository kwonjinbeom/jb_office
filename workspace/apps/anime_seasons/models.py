from django.db import models

from apps.core.models import TrashableModel


class SeasonAnime(TrashableModel):
    """분기 방영작 하나 (2026-10-23 사용자: memorily 티스토리 › 분기별 애니 추천 및 후기).
    분기 목록에서 본 것을 '본 애니'로 옮기고(watched), 평점·한 줄 평·감상평을 적어 분기 추천 글의 글감으로 쓴다.
    분기는 방영 시작일 기준 (1~3월 = 1분기). 평점은 별 반 개 단위라 1~10 으로 둔다 (7 = ★3.5)."""

    year = models.PositiveSmallIntegerField("연도", db_index=True)
    quarter = models.PositiveSmallIntegerField("분기", choices=[(q, f"{q}분기") for q in range(1, 5)])
    title = models.CharField("제목", max_length=200)
    original_title = models.CharField("원제", max_length=200, blank=True)
    aired = models.DateField("방영 시작", null=True, blank=True)
    genre = models.CharField("장르", max_length=120, blank=True)
    episodes = models.PositiveSmallIntegerField("화수", null=True, blank=True)
    watched = models.BooleanField("봄", default=False)
    watched_at = models.DateTimeField("옮긴 때", null=True, blank=True)
    rating = models.PositiveSmallIntegerField("평점", null=True, blank=True, help_text="1~10 (별 반 개 단위)")
    pick = models.BooleanField("추천", default=False)
    one_line = models.CharField("한 줄 평", max_length=120, blank=True)
    review = models.TextField("감상평", blank=True)
    created_at = models.DateTimeField("만든 날", auto_now_add=True)
    updated_at = models.DateTimeField("수정일", auto_now=True)

    class Meta:
        ordering = ["year", "quarter", "aired", "title"]
        verbose_name = "분기 애니"
        verbose_name_plural = "분기 애니"

    def __str__(self):
        return self.title

    @property
    def stars(self):
        """★ 표시용 (7 → 3.5)."""
        return self.rating / 2 if self.rating else None
