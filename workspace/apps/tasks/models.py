from django.db import models
from apps.core.models import TrashableModel
from django.urls import reverse
from django.utils import timezone


class Task(TrashableModel):
    """아이디어(또는 그 단계)에 달린 다음 행동 하나."""

    title = models.CharField("할 일", max_length=200)
    idea = models.ForeignKey(
        "ideas.Idea", verbose_name="아이디어", null=True, blank=True, on_delete=models.SET_NULL, related_name="tasks"
    )
    stage = models.ForeignKey(
        "ideas.Stage", verbose_name="단계", null=True, blank=True, on_delete=models.SET_NULL, related_name="tasks"
    )
    due = models.DateField("마감", null=True, blank=True)
    done = models.BooleanField("완료", default=False)
    done_at = models.DateTimeField("완료 시각", null=True, blank=True)
    notes = models.TextField("메모", blank=True)
    created_at = models.DateTimeField("생성", auto_now_add=True)
    updated_at = models.DateTimeField("수정", auto_now=True)

    class Meta:
        ordering = ["done", "due", "-created_at"]
        verbose_name = "할 일"
        verbose_name_plural = "할 일"

    def __str__(self) -> str:
        return self.title

    def get_absolute_url(self) -> str:
        return reverse("tasks:edit", args=[self.pk])

    def set_done(self, value: bool) -> None:
        self.done = value
        self.done_at = timezone.now() if value else None
        self.save(update_fields=["done", "done_at", "updated_at"])

    @property
    def is_overdue(self) -> bool:
        return bool(self.due and not self.done and self.due < timezone.localdate())
