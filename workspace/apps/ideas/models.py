from django.db import models
from apps.core.models import TrashableModel
from django.urls import reverse


class Idea(TrashableModel):
    """시장조사에서 나온 후보 하나. 02_후보원장.md / 11_통합시장지도.md 의 행 하나에 대응한다."""

    class Category(models.TextChoices):
        REQUEST = "request", "직접 의뢰"
        MARKET = "market", "마켓 상품"
        PRODUCT = "product", "독립 상품·도구"
        CONTENT = "content", "플랫폼 글"
        SOCIAL = "social", "소셜 콘텐츠"
        SEARCH = "search", "검색·제휴"
        DATA = "data", "데이터"
        ASSET = "asset", "스톡·에셋"
        OTHER = "other", "기타"

    class Status(models.TextChoices):
        CANDIDATE = "candidate", "후보"
        REVIEW = "review", "검토중"
        EXPERIMENT = "experiment", "초기 실험군"
        ACTIVE = "active", "진행중"
        RESERVE = "reserve", "예비축"
        HOLD = "hold", "보류"
        DROPPED = "dropped", "폐기"

    PRIORITY_CHOICES = [(5, "5 · 최우선"), (4, "4 · 높음"), (3, "3 · 보통"), (2, "2 · 낮음"), (1, "1 · 참고")]

    code = models.CharField("코드", max_length=10, unique=True, help_text="예: C01")
    title = models.CharField("제목", max_length=200)
    category = models.CharField("분류", max_length=20, choices=Category.choices, default=Category.OTHER)
    status = models.CharField("상태", max_length=20, choices=Status.choices, default=Status.CANDIDATE)
    priority = models.PositiveSmallIntegerField("우선순위", choices=PRIORITY_CHOICES, default=3)

    customer = models.CharField("고객·독자", max_length=200, blank=True)
    pain = models.TextField("불편·욕구", blank=True)
    current_alternative = models.TextField("현재 지출·대안", blank=True)
    money_flow = models.TextField("돈이 생기는 방식", blank=True)
    evidence = models.TextField("증거·수요 신호", blank=True)
    min_product = models.TextField("최소 판매물·공개물", blank=True)
    channel = models.TextField("첫 고객·유통 경로", blank=True)
    risk = models.TextField("핵심 위험", blank=True)
    judgement = models.TextField("현재 판단", blank=True)
    notes = models.TextField("작업 메모", blank=True, help_text="조사하면서 추가하는 자유 메모")

    source_doc = models.CharField("출처 문서", max_length=200, blank=True)
    tags = models.CharField("태그", max_length=200, blank=True, help_text="쉼표로 구분")

    created_at = models.DateTimeField("생성", auto_now_add=True)
    updated_at = models.DateTimeField("수정", auto_now=True)

    class Meta:
        ordering = ["code"]
        verbose_name = "아이디어"
        verbose_name_plural = "아이디어"

    def __str__(self) -> str:
        return f"{self.code} {self.title}"

    def get_absolute_url(self) -> str:
        return reverse("ideas:detail", args=[self.pk])

    @property
    def tag_list(self) -> list[str]:
        return [t.strip() for t in self.tags.split(",") if t.strip()]

    @property
    def status_tone(self) -> str:
        """배지 색상 톤. CSS 의 .badge.<tone> 과 짝을 이룬다."""
        return {
            self.Status.EXPERIMENT: "blue",
            self.Status.ACTIVE: "green",
            self.Status.REVIEW: "amber",
            self.Status.RESERVE: "violet",
            self.Status.HOLD: "gray",
            self.Status.DROPPED: "red",
        }.get(self.status, "slate")

    @property
    def current_stage(self):
        """진행 중인 단계가 있으면 그것, 없으면 첫 번째 대기 단계."""
        stages = list(self.stages.all())
        for st in stages:
            if st.status == Stage.Status.DOING:
                return st
        for st in stages:
            if st.status == Stage.Status.TODO:
                return st
        return None

    @property
    def stage_progress(self) -> tuple[int, int]:
        stages = list(self.stages.all())
        done = sum(1 for s in stages if s.status == Stage.Status.DONE)
        return done, len(stages)


class Stage(TrashableModel):
    """아이디어를 실현하는 세부 단계 하나. 순서대로 진행한다."""

    class Status(models.TextChoices):
        TODO = "todo", "대기"
        DOING = "doing", "진행"
        DONE = "done", "완료"
        HOLD = "hold", "보류"

    idea = models.ForeignKey(Idea, verbose_name="아이디어", on_delete=models.CASCADE, related_name="stages")
    order = models.PositiveIntegerField("순서", default=0)
    title = models.CharField("단계", max_length=200)
    goal = models.TextField("이 단계의 목표", blank=True, help_text="끝났다고 말할 수 있는 조건")
    status = models.CharField("상태", max_length=10, choices=Status.choices, default=Status.TODO)
    due = models.DateField("마감", null=True, blank=True)
    result = models.TextField("결과·배운 것", blank=True)
    created_at = models.DateTimeField("생성", auto_now_add=True)
    updated_at = models.DateTimeField("수정", auto_now=True)

    class Meta:
        ordering = ["idea", "order", "id"]
        verbose_name = "단계"
        verbose_name_plural = "단계"

    def __str__(self) -> str:
        return f"{self.idea.code} · {self.order}. {self.title}"

    def get_absolute_url(self) -> str:
        return reverse("ideas:stage_edit", args=[self.idea_id, self.pk])

    @property
    def status_tone(self) -> str:
        return {"todo": "slate", "doing": "blue", "done": "green", "hold": "gray"}[self.status]

    @property
    def is_overdue(self) -> bool:
        from django.utils import timezone

        return bool(self.due and self.status not in {self.Status.DONE, self.Status.HOLD} and self.due < timezone.localdate())


class IdeaLog(TrashableModel):
    """아이디어 작업 로그. 날짜순으로 쌓이는 짧은 기록."""

    idea = models.ForeignKey(Idea, verbose_name="아이디어", on_delete=models.CASCADE, related_name="logs")
    stage = models.ForeignKey(Stage, verbose_name="단계", null=True, blank=True, on_delete=models.SET_NULL, related_name="logs")
    body = models.TextField("내용")
    created_at = models.DateTimeField("기록", auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "작업 로그"
        verbose_name_plural = "작업 로그"

    def __str__(self) -> str:
        return f"{self.idea.code} {self.created_at:%Y-%m-%d} {self.body[:30]}"
