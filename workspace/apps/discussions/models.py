from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse
from django.utils import timezone


class Discussion(models.Model):
    AREA_CHOICES = [("blog", "블로그·카페"), ("video", "영상 콘텐츠"), ("ideas", "내 아이디어"), ("daily_ideas", "일일 아이디어"), ("memos", "메모"), ("docs", "문서"), ("other", "기타")]

    class Status(models.TextChoices):
        NEW = "new", "미논의"
        TALK = "talk", "논의 중"
        DECIDED = "decided", "결정"
        ACTIVE = "active", "진행"
        HOLD = "hold", "보류"
        DONE = "done", "완료"

    class Amount(models.TextChoices):
        NONE = "none", "아직"
        LITTLE = "little", "조금"
        SEVERAL = "several", "여러 번"
        MUCH = "much", "많이"

    class Partner(models.TextChoices):
        NONE = "none", "미정"
        CODEX = "codex", "Codex"
        CLAUDE = "claude", "Claude"
        BOTH = "both", "둘 다"

    area = models.CharField("메뉴", max_length=20, choices=AREA_CHOICES, default="other")
    parent = models.ForeignKey("self", verbose_name="상위 주제", null=True, blank=True, on_delete=models.PROTECT, related_name="children")
    name = models.CharField("논의 주제", max_length=80)
    summary = models.CharField("현재 핵심", max_length=140, blank=True, help_text="한 문장만. 최대 140자.")
    next_action = models.CharField("다음 행동", max_length=80, blank=True, help_text="할 일 하나만. 최대 80자.")
    status = models.CharField("상태", max_length=12, choices=Status.choices, default=Status.NEW)
    amount = models.CharField("대화량", max_length=12, choices=Amount.choices, default=Amount.NONE)
    partner = models.CharField("대화 상대", max_length=12, choices=Partner.choices, default=Partner.NONE)
    idea = models.ForeignKey("ideas.Idea", verbose_name="관련 아이디어", null=True, blank=True, on_delete=models.SET_NULL)
    content = models.ForeignKey("content.Content", verbose_name="관련 콘텐츠", null=True, blank=True, on_delete=models.SET_NULL)
    updated_at = models.DateTimeField("최근 변경", auto_now=True)
    created_at = models.DateTimeField("등록", default=timezone.now, editable=False)

    class Meta:
        ordering = ["-updated_at", "-pk"]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("discussions:detail", args=[self.pk])

    def clean(self):
        super().clean()
        seen = {self.pk} if self.pk else set()
        node = self.parent if self.parent_id else None
        while node:
            if node.pk in seen:
                raise ValidationError({"parent": "자신이나 하위 주제를 상위 주제로 선택할 수 없습니다."})
            if node.area != self.area:
                raise ValidationError({"parent": "같은 메뉴의 주제를 선택하세요."})
            seen.add(node.pk)
            node = node.parent
        if self.pk and self.children.exclude(area=self.area).exists():
            raise ValidationError({"area": "하위 주제가 있으면 메뉴를 변경할 수 없습니다."})
        if self.content_id and self.area != self.content.workspace:
            raise ValidationError({"content": "관련 콘텐츠와 같은 메뉴를 선택하세요."})


class DiscussionHistory(models.Model):
    discussion = models.ForeignKey(Discussion, on_delete=models.CASCADE, related_name="history")
    summary = models.CharField(max_length=140, blank=True)
    next_action = models.CharField(max_length=80, blank=True)
    status = models.CharField(max_length=12, choices=Discussion.Status.choices)
    amount = models.CharField(max_length=12, choices=Discussion.Amount.choices)
    partner = models.CharField(max_length=12, choices=Discussion.Partner.choices)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-pk"]
