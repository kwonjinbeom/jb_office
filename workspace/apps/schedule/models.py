from django.db import models

from apps.core.models import TrashableModel


class Event(TrashableModel):
    """일정 하나 (2026-10-22 사용자: 대메뉴 '일정관리' — 큰 달력 + 그날 목록 + 입력·수정 폼). 시각은 비워도 된다(하루 종일)."""

    date = models.DateField("날짜", db_index=True)
    time = models.TimeField("시각", null=True, blank=True, help_text="비우면 하루 종일")
    title = models.CharField("일정", max_length=120)
    note = models.TextField("메모", blank=True)
    done = models.BooleanField("완료", default=False)
    created_at = models.DateTimeField("만든 날", auto_now_add=True)
    updated_at = models.DateTimeField("수정일", auto_now=True)

    class Meta:
        ordering = ["date", "time", "pk"]
        verbose_name = "일정"
        verbose_name_plural = "일정"

    def __str__(self):
        return self.title
