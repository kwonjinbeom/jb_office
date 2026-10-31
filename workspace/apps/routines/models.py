"""일일루틴: 화면(메뉴)마다 AI 에게 맡길 하루 양과 프롬프트.

프롬프트는 저장소 md (일일루틴/프롬프트/<키>.md). 예약(클라우드)·실행(PC) 모두 같은 md 를 본다.
실행할 때는 짧은 안내문(날짜·하루 양·오늘의 자료)만 만들어 넘긴다 (views.launcher).
평가(Evaluation)를 쌓고 '갱신'하면 AI 가 그 md 를 고친다. 바뀐 md 는 PromptVersion 으로 남는다.
"""
from django.db import models
from django.utils import timezone

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
    """루틴 실행 한 번 (매일 아침 예약 · 화면의 '실행'). claude 가 단계마다 서버의 보고 주소(views.report)나
    PC 의 `manage.py routine_report` 로 상태와 한 줄을 남긴다. 일일루틴 화면 오른쪽 아래 '실행 이력'."""

    class Status(models.TextChoices):
        RUNNING = "running", "진행"
        WAITING = "waiting", "대기"
        BLOCKED = "blocked", "막힘"
        DONE = "done", "완료"
        FAILED = "failed", "실패"

    class Via(models.TextChoices):
        RUN = "run", "실행"
        SCHEDULE = "schedule", "예약"

    # 보고 말 → 상태 (안내문의 '진행 보고'가 이 말을 쓴다)
    WORDS = {"시작": Status.RUNNING, "진행": Status.RUNNING, "대기": Status.WAITING,
             "막힘": Status.BLOCKED, "완료": Status.DONE, "실패": Status.FAILED}

    routine = models.ForeignKey(Routine, verbose_name="루틴", on_delete=models.CASCADE, related_name="runs")
    day = models.DateField("날짜")
    status = models.CharField("상태", max_length=10, choices=Status.choices, default=Status.RUNNING)
    step = models.CharField("지금 단계", max_length=200, blank=True)
    log = models.TextField("기록", blank=True)
    via = models.CharField("어떻게", max_length=10, choices=Via.choices, default=Via.RUN)
    started_at = models.DateTimeField("시작", auto_now_add=True)
    updated_at = models.DateTimeField("마지막 보고", auto_now=True)

    class Meta:
        ordering = ["-updated_at", "-pk"]
        verbose_name = "루틴 실행"
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

    @classmethod
    def record(cls, routine, day, word, message="", via=None):
        """보고 한 줄을 남긴다. '시작'은 그날 끝나지 않은 기록이 있으면 이어 쓰고, 없으면 새로 만든다."""
        run = cls.objects.filter(routine=routine, day=day).first()
        if run is None or (word == "시작" and not run.is_open):
            run = cls.objects.create(routine=routine, day=day, via=via or cls.Via.RUN)
        run.report(cls.WORDS[word], message or word, timezone.localtime())
        return run

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
    """글쓰기 루틴의 그날 분류·편수 ({"c3": 2, "t5": 1}). 없으면 그날의 기본 (AI 소식 1 고정 · 정보 6 · 소개 4 무작위)."""

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


class FixedTopic(TrashableModel):
    """커스텀 글쓰기의 고정 주제 (2026-10-21 사용자): 주제·지침이 정해진 글. 예) 공모주 일정 · 국내 / 해외, 청년·신혼 정책.
    글 분류의 소재 아래에 있다 (2026-10-23 사용자: 공모주 일정 국내·해외는 눈잎 > 공모주 아래). 실행은 topics.run."""

    name = models.CharField("주제", max_length=60)
    site = models.CharField("사이트", max_length=60, blank=True, help_text="올릴 사이트 (비우면 주제에 맞게 고른다)")
    category = models.ForeignKey("blog_types.Category", verbose_name="소재", null=True, blank=True, on_delete=models.SET_NULL,
                                 related_name="fixed_topics", help_text="글 분류의 소재. 커스텀 글쓰기에서 그 소재 아래에 보이고 원고 분류가 된다")
    note = models.TextField("지침", blank=True, help_text="이 주제를 쓸 때 따로 지킬 것 (다룰 범위·출처·구성 등)")
    per_week = models.PositiveSmallIntegerField("주당 편수", default=1)
    daily = models.BooleanField("매일 전체 실행", default=False,
                                help_text="일일루틴 전체 실행(글쓰기)에서 매일 1편 쓴다 (2026-10-23 사용자: AI 소식)")
    order = models.PositiveSmallIntegerField("순서", default=0)
    created_at = models.DateTimeField("만든 때", auto_now_add=True)

    class Meta:
        ordering = ["order", "pk"]
        verbose_name = "고정 주제"
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name


class TopicWeek(models.Model):
    """고정 주제의 한 주: 발행했는지 (사용자가 직접 표시한다). week 는 그 주 월요일."""

    topic = models.ForeignKey(FixedTopic, verbose_name="주제", on_delete=models.CASCADE, related_name="weeks")
    week = models.DateField("주 (월요일)")
    published = models.BooleanField("발행", default=False)
    updated_at = models.DateTimeField("고친 때", auto_now=True)

    class Meta:
        verbose_name = "고정 주제 주간"
        verbose_name_plural = verbose_name
        constraints = [models.UniqueConstraint(fields=["topic", "week"], name="routines_topicweek_unique")]

    def __str__(self):
        return f"{self.topic} {self.week}"


class FollowUp(models.Model):
    """이어서 할 일 (2026-10-31 사용자): 글쓰기·변환 터미널이 끝까지 못 하고 끝났을 때, 무엇이 남았는지 짧게 남긴 한 건.
    터미널은 열렸다 닫히니 어디서 멈췄는지 알 수 없었다 → claude 가 끝낼 때 보고 주소(followups.api_new)로 남기거나,
    화면에서 실행 이력(실패·막힘·멈춤)을 골라 올린다. '이어서 하기'로 PC 터미널에서 다시 하고, 끝나면 완료가 된다."""

    class Status(models.TextChoices):
        OPEN = "open", "남음"
        RUNNING = "running", "이어서 하는 중"
        DONE = "done", "완료"
        DROPPED = "dropped", "안 함"

    class Source(models.TextChoices):
        WRITING = "writing", "글쓰기"
        CONVERT = "convert", "변환"
        ANIME = "anime", "애니"
        ROUTINE = "routine", "루틴"
        OTHER = "other", "기타"

    title = models.CharField("남은 일", max_length=200)
    source = models.CharField("어디서", max_length=10, choices=Source.choices, default=Source.OTHER)
    routine = models.ForeignKey(Routine, verbose_name="루틴", null=True, blank=True, on_delete=models.SET_NULL, related_name="followups")
    run = models.ForeignKey(RoutineRun, verbose_name="실행", null=True, blank=True, on_delete=models.SET_NULL, related_name="followups")
    day = models.DateField("날짜")
    # 다시 확인 (2026-10-31 사용자): 막혀서가 아니라 정보가 아직 안 나와 그날 다시 찾아야 하는 일 (예: 11/1 0시에 공개되는 올영 블프 쿠폰).
    # 있으면 '확인이 필요한 것' 칸에 그날까지 '기다림', 그날부터 '확인할 때'로 보인다.
    check_on = models.DateField("다시 확인할 날", null=True, blank=True)
    why = models.TextField("멈춘 까닭", blank=True)
    next_steps = models.TextField("이어서 할 일", blank=True)
    status = models.CharField("상태", max_length=10, choices=Status.choices, default=Status.OPEN)
    log = models.TextField("기록", blank=True)
    created_at = models.DateTimeField("남긴 때", auto_now_add=True)
    updated_at = models.DateTimeField("고친 때", auto_now=True)
    resolved_at = models.DateTimeField("끝낸 때", null=True, blank=True)

    BADGES = {"open": "amber", "running": "blue", "done": "green", "dropped": "gray"}
    SOURCE_BADGES = {"writing": "outline", "convert": "violet", "anime": "outline", "routine": "outline", "other": "gray"}

    class Meta:
        ordering = ["-created_at", "-pk"]
        verbose_name = "이어서 할 일"
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.title

    @property
    def badge(self):
        return self.BADGES.get(self.status, "gray")

    @property
    def source_badge(self):
        return self.SOURCE_BADGES.get(self.source, "gray")

    @property
    def is_open(self):
        return self.status in (self.Status.OPEN, self.Status.RUNNING)

    @property
    def waiting(self):
        """다시 확인할 날이 아직 오지 않았다."""
        return self.check_on is not None and self.status == self.Status.OPEN and self.check_on > timezone.localdate()

    @property
    def state(self):
        """화면의 상태 글: 다시 확인할 일은 그날 전 '기다림', 그날부터 '확인할 때'."""
        if self.check_on is not None and self.status == self.Status.OPEN:
            return "기다림" if self.waiting else "확인할 때"
        return self.get_status_display()

    @property
    def state_badge(self):
        return "gray" if self.waiting else self.badge

    def note(self, message, status=None):
        """기록에 한 줄 더하고 (상태를 바꾼다). 완료·안 함이면 끝낸 때를, 다시 열면 지운다."""
        if status:
            self.status = status
            self.resolved_at = timezone.now() if status in (self.Status.DONE, self.Status.DROPPED) else None
        line = f"{timezone.localtime():%m-%d %H:%M} {self.get_status_display()} · {message}"
        self.log = f"{self.log}\n{line}" if self.log else line
        self.save()
