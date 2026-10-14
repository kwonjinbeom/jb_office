from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.urls import reverse


class WritingProfile(models.Model):
    name = models.CharField("작성 규칙 이름", max_length=80)
    blog_url = models.URLField(
        "티스토리 블로그 주소",
        blank=True,
        max_length=300,
        help_text="예: https://내블로그.tistory.com",
    )
    audience = models.CharField("주 독자", max_length=200, blank=True)
    tone = models.CharField(
        "말투·분위기",
        max_length=200,
        default="쉽고 담백한 존댓말. 과장 없이 구체적으로.",
    )
    rules = models.TextField(
        "작성 기준",
        blank=True,
        help_text="피할 표현, 문단 구성, 출처 기준 등을 적으세요.",
    )
    closing = models.CharField("기본 마무리 방향", max_length=300, blank=True)
    disclosure = models.CharField(
        "제휴·광고 표시 문구",
        max_length=500,
        blank=True,
        help_text="실제 해당하는 원고에서만 사용합니다.",
    )
    target_length = models.PositiveIntegerField(
        "목표 글자 수",
        default=1600,
        validators=[MinValueValidator(200), MaxValueValidator(20000)],
        help_text="작성 분량을 가늠하는 기준이며 검색 노출 기준이 아닙니다.",
    )

    class Meta:
        ordering = ["name", "pk"]

    def __str__(self):
        return self.name


class WritingTemplate(models.Model):
    name = models.CharField("템플릿 이름", max_length=80)
    description = models.CharField("용도", max_length=200, blank=True)
    body = models.TextField(
        "본문 틀",
        help_text="Markdown으로 작성. {{answer}}, {{question}}, {{experience}}, {{closing}}을 사용할 수 있습니다. 미작성 부분은 [[작성할 내용]]으로 표시하세요.",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name", "pk"]

    def __str__(self):
        return self.name


class Draft(models.Model):
    content = models.OneToOneField(
        "content.Content", on_delete=models.CASCADE, related_name="writing_draft"
    )
    profile = models.ForeignKey(
        WritingProfile,
        verbose_name="작성 규칙",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    template_key = models.CharField("글 형식", max_length=60, default="howto")
    keyword = models.CharField("중심 검색어", max_length=100, blank=True)
    tags = models.CharField(
        "태그", max_length=300, blank=True, help_text="쉼표로 구분, 최대 10개"
    )
    question = models.TextField("독자가 궁금한 것", blank=True)
    answer = models.CharField("답·핵심 한 줄", max_length=300, blank=True)
    experience = models.TextField("직접 확인·경험한 것", blank=True)
    description = models.CharField(
        "글 소개",
        max_length=300,
        blank=True,
        help_text="검색 결과와 공유에서 보여줄 내용을 짧게 작성",
    )
    commercial = models.BooleanField("광고·제휴가 있는 글", default=False)
    sources = models.JSONField(default=list, blank=True)
    checks = models.JSONField(default=list, blank=True)
    revision = models.PositiveIntegerField(default=1)
    published_url = models.URLField("게시 URL", blank=True, max_length=500)
    published_on = models.DateField("게시일", null=True, blank=True)

    class Meta:
        ordering = ["-content__updated_at", "-pk"]

    def __str__(self):
        return self.content.title

    def get_absolute_url(self):
        return reverse("writing:editor", args=[self.pk])


class DraftRevision(models.Model):
    draft = models.ForeignKey(Draft, on_delete=models.CASCADE, related_name="versions")
    label = models.CharField(max_length=80)
    payload = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-pk"]
