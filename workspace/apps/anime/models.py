from django.db import models

from apps.core.models import TrashableModel


class AnimeTitle(TrashableModel):
    """애니 총정리의 전체 애니 목록 한 줄 (2026-10-23 사용자: 왼쪽 전체 목록에서 골라 '작업 순서 · 작품'에 담는다).
    담은(picked) 작품만 가운데 칸에 나온다. 작품 md 가 있으면 doc_key(파일 이름, 예: 01_나루토)로 잇는다."""

    STATUS = [("todo", "대기"), ("doing", "작업 중"), ("written", "원고 완료"), ("published", "발행 완료")]

    title = models.CharField("제목", max_length=120)
    note = models.CharField("메모", max_length=80, blank=True, help_text="방영 시작 해 등 짧게")
    status = models.CharField("상태", max_length=12, choices=STATUS, default="todo")
    picked = models.BooleanField("담음", default=False)
    order = models.PositiveIntegerField("순서", default=0, help_text="유명한 순 (작을수록 위)")
    doc_key = models.CharField("작품 md", max_length=80, blank=True)
    created_at = models.DateTimeField("만든 날", auto_now_add=True)
    updated_at = models.DateTimeField("수정일", auto_now=True)

    class Meta:
        ordering = ["order", "pk"]
        verbose_name = "애니"
        verbose_name_plural = "애니"

    def __str__(self):
        return self.title
