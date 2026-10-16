"""일일루틴: 화면(메뉴)마다 AI 에게 맡길 하루 양과 프롬프트. 로컬(PC 터미널)과 클라우드는 프롬프트가 다르다.

로컬: 이 PC 저장소에서 claude 를 돌린다. 티스토리·네이버를 직접 볼 수 있고 main 에 push 한다.
클라우드: 클라우드 세션에 프롬프트를 직접 보낸다. 사이트를 제대로 못 보니 이미 있는 글 목록을 프롬프트에 넣고, PR 로 올린다.
"""
from django.db import models

PLACEHOLDERS = "{날짜} {하루양} {사이트} {기존글} {검색표준}"


class Routine(models.Model):
    key = models.SlugField("키", max_length=30, unique=True)
    name = models.CharField("메뉴", max_length=40)
    url_name = models.CharField("화면 주소 이름", max_length=60)
    task = models.CharField("할 일", max_length=120)
    output = models.CharField("결과 위치", max_length=200, blank=True)
    daily = models.PositiveSmallIntegerField("하루 양", default=1)
    unit = models.CharField("단위", max_length=10, default="개")
    prompt_local = models.TextField("로컬 프롬프트", help_text=f"PC 터미널용. 바뀌는 칸: {PLACEHOLDERS}")
    prompt_cloud = models.TextField("클라우드 프롬프트", help_text=f"클라우드 세션용. 바뀌는 칸: {PLACEHOLDERS}")
    order = models.PositiveSmallIntegerField("순서", default=0)

    class Meta:
        ordering = ["order", "pk"]
        verbose_name = "일일루틴"
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name


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
