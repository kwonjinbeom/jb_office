"""로컬로 돌리는 claude 가 일일루틴 화면에 진행 현황을 남기는 명령.

    workspace/.venv/Scripts/python workspace/manage.py routine_report tistory 진행 "원고 2/4편 저장"

상태: 시작 · 진행 · 대기(내가 할 일이 있음) · 막힘(그 단계를 못 함) · 완료 · 실패.
'시작'은 그날 끝나지 않은 기록이 있으면 이어 쓰고, 없으면 새로 만든다.
"""
from datetime import date

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.routines.models import Routine, RoutineRun

WORDS = {
    "시작": RoutineRun.Status.RUNNING, "진행": RoutineRun.Status.RUNNING, "대기": RoutineRun.Status.WAITING,
    "막힘": RoutineRun.Status.BLOCKED, "완료": RoutineRun.Status.DONE, "실패": RoutineRun.Status.FAILED,
}


class Command(BaseCommand):
    help = "일일루틴 로컬 실행 현황 남기기: <루틴 키> <시작|진행|대기|막힘|완료|실패> <한 줄>"

    def add_arguments(self, parser):
        parser.add_argument("key")
        parser.add_argument("status", choices=list(WORDS))
        parser.add_argument("message", nargs="?", default="")
        parser.add_argument("--date", dest="day", default="")

    def handle(self, key, status, message, day, **options):
        routine = Routine.objects.filter(key=key).first()
        if routine is None:
            raise CommandError(f"루틴 키가 없습니다: {key} (있는 키: {', '.join(Routine.objects.values_list('key', flat=True))})")
        try:
            day = date.fromisoformat(day) if day else timezone.localdate()
        except ValueError:
            raise CommandError("--date 는 YYYY-MM-DD") from None
        run = RoutineRun.objects.filter(routine=routine, day=day).first()
        if run is None or (status == "시작" and not run.is_open):
            run = RoutineRun.objects.create(routine=routine, day=day)
        run.report(WORDS[status], message or status, timezone.localtime())
        self.stdout.write(f"ok {routine.key} {day} {run.status}")  # 터미널 인코딩과 상관없이 읽히게
