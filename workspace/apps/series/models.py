"""memorily 연재 (2026-10-20 사용자): 이 저장소에서 AI(Claude·Codex)와 블로그 자동화를 만든 과정을 에피소드로 나눠 쓴다.

에피소드 하나 = 실제로 겪은 한 구간 (커밋·문서·PR 이 근거). '글로 만들기'를 누르면 memorily 사이트의 임시글이 생기고
(사이트별 템플릿의 memorily 구성: 겪은 상황 → 해 본 것 → 결과와 느낀 점 → 다음에 해 볼 것), 그 뒤는 글 관리 흐름을 탄다.
"""
from django.db import models


class Episode(models.Model):
    class Status(models.TextChoices):
        # 값은 공통 상태 버튼 색(todo·doing·done)을 그대로 쓰려고 맞췄다
        PLAN = "todo", "계획"
        WRITING = "doing", "쓰는 중"
        DONE = "done", "발행"

    number = models.PositiveIntegerField("회차", unique=True)
    title = models.CharField("제목", max_length=200)
    hook = models.CharField("한 줄", max_length=300, blank=True, help_text="이 회차에서 겪은 것 한 문장")
    period = models.CharField("기간", max_length=40, blank=True, help_text="예: 10-13 ~ 10-15")
    points = models.TextField("다룰 것", blank=True, help_text="한 줄에 하나")
    sources = models.TextField("근거", blank=True, help_text="커밋·문서·PR, 한 줄에 하나")
    status = models.CharField("상태", max_length=10, choices=Status.choices, default=Status.PLAN)
    post = models.ForeignKey("writing.Post", verbose_name="글", null=True, blank=True, on_delete=models.SET_NULL,
                             related_name="episodes")
    updated_at = models.DateTimeField("수정일", auto_now=True)

    class Meta:
        ordering = ["number"]
        verbose_name = "연재 회차"
        verbose_name_plural = "연재 회차"

    def __str__(self):
        return f"EP.{self.number} {self.title}"

    @property
    def point_list(self):
        return [line.strip(" -·") for line in self.points.splitlines() if line.strip(" -·")]

    @property
    def source_list(self):
        return [line.strip(" -·") for line in self.sources.splitlines() if line.strip(" -·")]
