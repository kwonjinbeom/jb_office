from django.core.exceptions import ValidationError
from django.db import models
from apps.core.models import TrashableModel
from django.urls import reverse


class Workspace(models.TextChoices):
    BLOG = "blog", "블로그·카페"
    VIDEO = "video", "영상 콘텐츠"


class Folder(TrashableModel):
    workspace = models.CharField("공간", max_length=10, choices=Workspace.choices)
    name = models.CharField("폴더 이름", max_length=80)
    parent = models.ForeignKey("self", verbose_name="상위 폴더", null=True, blank=True, on_delete=models.PROTECT, related_name="children")
    audience = models.CharField("독자·시청자", max_length=120, blank=True)
    purpose = models.CharField("목적", max_length=140, blank=True)
    tone = models.CharField("말투·분위기", max_length=120, blank=True)
    rules = models.TextField("작성·제작 규칙", blank=True, help_text="기본 구성, 길이, 근거·출처 기준 등을 짧게 적으세요.")

    class Meta:
        ordering = ["name", "pk"]

    def __str__(self):
        return self.name

    def clean(self):
        super().clean()
        seen = {self.pk} if self.pk else set()
        node = self.parent if self.parent_id else None
        while node:
            if node.pk in seen:
                raise ValidationError({"parent": "자신이나 하위 폴더를 상위 폴더로 선택할 수 없습니다."})
            if node.workspace != self.workspace:
                raise ValidationError({"parent": "같은 공간의 폴더를 선택하세요."})
            seen.add(node.pk)
            node = node.parent

    def get_absolute_url(self):
        return reverse(f"{self.workspace}:list") + f"?folder={self.pk}"


class Content(TrashableModel):
    class Kind(models.TextChoices):
        TOPIC = "topic", "소재"
        TEMPLATE = "template", "템플릿"
        WORK = "work", "글·영상"

    class Status(models.TextChoices):
        TOPIC = "topic", "소재"
        PLAN = "plan", "기획"
        DRAFT = "draft", "초안"
        REVIEW = "review", "검토"
        READY = "ready", "게시 준비"
        PUBLISHED = "published", "게시 완료"
        HOLD = "hold", "보류"

    workspace = models.CharField("공간", max_length=10, choices=Workspace.choices)
    folder = models.ForeignKey(Folder, verbose_name="폴더", null=True, blank=True, on_delete=models.PROTECT, related_name="contents")
    title = models.CharField("제목", max_length=160)
    kind = models.CharField("종류", max_length=12, choices=Kind.choices, default=Kind.TOPIC)
    status = models.CharField("상태", max_length=12, choices=Status.choices, default=Status.TOPIC)
    summary = models.CharField("핵심 한 줄", max_length=140, blank=True)
    outline = models.TextField("기획·구성", blank=True)
    body = models.TextField("본문·대본", blank=True)
    scenes = models.TextField("장면·제작 자료", blank=True)
    idea = models.ForeignKey("ideas.Idea", verbose_name="관련 아이디어", null=True, blank=True, on_delete=models.SET_NULL, related_name="contents")
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-updated_at", "-pk"]

    def __str__(self):
        return self.title

    def clean(self):
        super().clean()
        if self.folder_id and self.folder.workspace != self.workspace:
            raise ValidationError({"folder": "같은 공간의 폴더를 선택하세요."})

    def get_absolute_url(self):
        return reverse(f"{self.workspace}:detail", args=[self.pk])


class Publication(TrashableModel):
    content = models.ForeignKey(Content, on_delete=models.CASCADE, related_name="publications")
    channel = models.CharField("플랫폼·채널", max_length=80, help_text="예: 네이버 블로그 / 카페 이름 / YouTube Shorts / Instagram / TikTok")
    title = models.CharField("게시용 제목", max_length=160, blank=True)
    version = models.TextField("게시처별 변형", blank=True, help_text="도입부, 길이, 본문·자막 변경 등 필요한 차이만 기록")
    url = models.URLField("게시 URL", max_length=500, blank=True)
    published_on = models.DateField("게시일", null=True, blank=True)
    result = models.CharField("반응·다음 개선", max_length=140, blank=True)

    class Meta:
        ordering = ["pk"]

    def get_absolute_url(self):
        return self.content.get_absolute_url()
