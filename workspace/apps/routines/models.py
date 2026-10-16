"""일일루틴: 화면(메뉴)마다 AI 에게 맡길 하루 양과 프롬프트.

프롬프트는 저장소 md (일일루틴/프롬프트/<키>.md). 예약(클라우드)·실행(PC) 모두 같은 md 를 본다.
실행할 때는 짧은 안내문(날짜·하루 양·오늘의 자료)만 만들어 넘긴다 (views.launcher).
평가(Evaluation)를 쌓고 '갱신'하면 AI 가 그 md 를 고친다. 바뀐 md 는 PromptVersion 으로 남는다.
"""
from django.db import models

from apps.core.models import TrashableModel

DATA_CHOICES = [("sites", "사이트·체크"), ("existing", "이미 있는 글"), ("standard", "검색 표준"), ("evaluations", "루틴별 평가·점검 관점"),
                ("picks", "오늘 쓸 분류"), ("categories", "글 분류 전체")]


class Routine(TrashableModel):
    key = models.SlugField("키", max_length=30, unique=True)
    name = models.CharField("메뉴", max_length=40)
    url_name = models.CharField("화면 주소 이름", max_length=60)
    task = models.CharField("할 일", max_length=120)
    output = models.CharField("결과 위치", max_length=200, blank=True)
    daily = models.PositiveSmallIntegerField("하루 양", default=1)
    unit = models.CharField("단위", max_length=10, default="개")
    prompt_doc = models.CharField("프롬프트 md", max_length=200, blank=True, help_text="저장소 기준 경로 (예: 일일루틴/프롬프트/tistory.md)")
    data = models.CharField("오늘의 자료", max_length=60, blank=True, help_text="실행 안내문에 붙일 자료 (서버 DB 에서 가져옴)")
    review_focus = models.TextField("갱신 때 볼 관점", blank=True, help_text="갱신할 때 평가와 함께 점검할 것 (예: 글쓰기면 사실 확인·중복·광고 정책)")
    # 예전에 DB 에 두던 프롬프트. 지금은 prompt_doc(md)을 쓴다. 지우지 않고 남겨 둔다.
    prompt_local = models.TextField("(예전) 로컬 프롬프트", blank=True, editable=False)
    prompt_cloud = models.TextField("(예전) 클라우드 프롬프트", blank=True, editable=False)
    order = models.PositiveSmallIntegerField("순서", default=0)

    class Meta:
        ordering = ["order", "pk"]
        verbose_name = "일일루틴"
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name

    @property
    def data_keys(self):
        return [k for k in self.data.split(",") if k]


class RoutineDay(models.Model):
    """일일루틴 화면에서 고친 그날 결과 수. 없으면 화면에서 자동으로 센 값."""

    routine = models.ForeignKey(Routine, verbose_name="루틴", on_delete=models.CASCADE, related_name="days")
    day = models.DateField("날짜")
    done = models.PositiveSmallIntegerField("결과")

    class Meta:
        verbose_name = "루틴 날짜별 결과"
        verbose_name_plural = verbose_name
        constraints = [models.UniqueConstraint(fields=["routine", "day"], name="routines_routineday_unique")]

    def __str__(self):
        return f"{self.routine} {self.day}"


class RoutineRun(models.Model):
    """로컬로 돌린 루틴 한 번. claude 가 단계마다 `manage.py routine_report` 로 상태와 한 줄을 남긴다."""

    class Status(models.TextChoices):
        RUNNING = "running", "진행"
        WAITING = "waiting", "대기"
        BLOCKED = "blocked", "막힘"
        DONE = "done", "완료"
        FAILED = "failed", "실패"

    routine = models.ForeignKey(Routine, verbose_name="루틴", on_delete=models.CASCADE, related_name="runs")
    day = models.DateField("날짜")
    status = models.CharField("상태", max_length=10, choices=Status.choices, default=Status.RUNNING)
    step = models.CharField("지금 단계", max_length=200, blank=True)
    log = models.TextField("기록", blank=True)
    started_at = models.DateTimeField("시작", auto_now_add=True)
    updated_at = models.DateTimeField("마지막 보고", auto_now=True)

    class Meta:
        ordering = ["-updated_at", "-pk"]
        verbose_name = "로컬 실행"
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"{self.routine} {self.day} {self.get_status_display()}"

    BADGES = {"running": "blue", "waiting": "amber", "blocked": "red", "done": "green", "failed": "red"}

    @property
    def badge(self):
        return self.BADGES.get(self.status, "gray")

    @property
    def is_open(self):
        return self.status in (self.Status.RUNNING, self.Status.WAITING, self.Status.BLOCKED)

    def report(self, status, message, at):
        self.status = status
        self.step = message[:200]
        line = f"{at:%H:%M} {self.Status(status).label} · {message}"
        self.log = f"{self.log}\n{line}" if self.log else line
        self.save()


class Evaluation(TrashableModel):
    """그날 루틴 결과물에 대한 나의 평가. 갱신 때 AI 가 읽고 프롬프트에 반영한다."""

    routine = models.ForeignKey(Routine, verbose_name="루틴", on_delete=models.CASCADE, related_name="evaluations")
    day = models.DateField("날짜")
    score = models.PositiveSmallIntegerField("평점", choices=[(i, f"{i}점") for i in range(1, 6)])
    comment = models.TextField("코멘트", blank=True)
    created_at = models.DateTimeField("남긴 때", auto_now_add=True)
    updated_at = models.DateTimeField("고친 때", auto_now=True)

    class Meta:
        ordering = ["-day", "-pk"]
        verbose_name = "루틴 평가"
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"{self.routine} {self.day} {self.score}점"


class PromptVersion(models.Model):
    """프롬프트 md 가 바뀔 때마다 남기는 내용. 프롬프트 관리 화면을 열 때 파일과 비교해 새로 남긴다."""

    routine = models.ForeignKey(Routine, verbose_name="루틴", on_delete=models.CASCADE, related_name="versions")
    number = models.PositiveIntegerField("버전")
    sha = models.CharField("내용 해시", max_length=64)
    content = models.TextField("내용")
    captured_at = models.DateTimeField("남긴 때", auto_now_add=True)
    starred = models.BooleanField("좋았던 버전", default=False)

    class Meta:
        ordering = ["-number"]
        verbose_name = "프롬프트 버전"
        verbose_name_plural = verbose_name
        constraints = [models.UniqueConstraint(fields=["routine", "number"], name="routines_promptversion_unique")]

    def __str__(self):
        return f"{self.routine} v{self.number}"


class RoutinePick(models.Model):
    """글쓰기 루틴의 그날 분류·편수 ({"c3": 2, "t5": 1}). 없으면 그날의 기본 무작위(광고 6 · 판매 3 · IT/AI 2)."""

    routine = models.ForeignKey(Routine, verbose_name="루틴", on_delete=models.CASCADE, related_name="picks")
    day = models.DateField("날짜")
    picks = models.JSONField("분류별 편수", default=dict)
    updated_at = models.DateTimeField("고친 때", auto_now=True)

    class Meta:
        verbose_name = "루틴 분류 고르기"
        verbose_name_plural = verbose_name
        constraints = [models.UniqueConstraint(fields=["routine", "day"], name="routines_routinepick_unique")]

    def __str__(self):
        return f"{self.routine} {self.day}"
