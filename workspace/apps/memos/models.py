from django.db import models
from django.urls import reverse


class Memo(models.Model):
    title = models.CharField("제목", max_length=200)
    body = models.TextField("내용", blank=True)
    pinned = models.BooleanField("상단 고정", default=False)
    tags = models.CharField("태그", max_length=200, blank=True, help_text="쉼표로 구분")
    created_at = models.DateTimeField("생성", auto_now_add=True)
    updated_at = models.DateTimeField("수정", auto_now=True)

    class Meta:
        ordering = ["-pinned", "-updated_at"]
        verbose_name = "메모"
        verbose_name_plural = "메모"

    def __str__(self) -> str:
        return self.title

    def get_absolute_url(self) -> str:
        return reverse("memos:detail", args=[self.pk])

    @property
    def tag_list(self) -> list[str]:
        return [t.strip() for t in self.tags.split(",") if t.strip()]

    @property
    def excerpt(self) -> str:
        text = " ".join(self.body.split())
        return text[:120] + ("…" if len(text) > 120 else "")
