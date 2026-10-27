from django.db import models

from apps.core.models import TrashableModel


REPEAT_CHOICES = [("", "한 번"), ("daily", "매일"), ("weekday", "평일")]


class Event(TrashableModel):
    """일정 하나 (2026-10-22 사용자: 대메뉴 '일정관리' — 큰 달력 + 그날 목록 + 입력·수정 폼). 시각은 비워도 된다(하루 종일)."""

    date = models.DateField("날짜", db_index=True)
    time = models.TimeField("시각", null=True, blank=True, help_text="비우면 하루 종일")
    title = models.CharField("일정", max_length=120)
    note = models.TextField("메모", blank=True)
    done = models.BooleanField("완료", default=False)
    # 반복 (2026-10-27 사용자: 'daily 알림' 목록): 매일·평일(월~금)은 날짜부터 날마다 그 시각에 알린다. 달력엔 안 나오고 따로 목록에. done 은 '끔'
    repeat = models.CharField("반복", max_length=10, choices=REPEAT_CHOICES, default="", blank=True)
    # 알림 (2026-10-22 사용자): 시각이 되면 우측 상단에 뜨고, 눌러야 들어간다. 누른 때를 적어 다시 뜨지 않게 (시각을 바꾸면 비운다)
    alarm_ack = models.DateTimeField("알림 확인", null=True, blank=True)  # 반복 일정은 오늘 누른 것만 '확인'으로 본다
    created_at = models.DateTimeField("만든 날", auto_now_add=True)
    updated_at = models.DateTimeField("수정일", auto_now=True)

    class Meta:
        ordering = ["date", "time", "pk"]
        verbose_name = "일정"
        verbose_name_plural = "일정"

    def __str__(self):
        return self.title
