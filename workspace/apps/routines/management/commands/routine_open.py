"""일일루틴 '실행' 링크(jbroutine:)를 받아 PC 에서 claude 터미널을 여는 명령. Windows 가 링크를 열 때 부른다.

    workspace/.venv/Scripts/python workspace/manage.py routine_open --pause "jbroutine:run?key=writing&day=2026-10-16"

안내문은 화면이 클립보드에 복사해 둔 것을 읽는다. 등록은 workspace/routine_link.bat (run.bat 이 부른다).
"""
from django.core.management import call_command
from django.core.management.base import BaseCommand

from apps.routines import local_run


class Command(BaseCommand):
    help = "일일루틴 실행 링크로 claude 터미널 열기 (안내문은 클립보드에서)"

    def add_arguments(self, parser):
        parser.add_argument("link")
        parser.add_argument("--pause", action="store_true", help="실패하면 창을 닫기 전에 기다린다 (링크로 열린 창)")

    def handle(self, link, pause, **options):
        try:
            call_command("migrate", interactive=False, verbosity=0)  # PC DB 가 코드보다 늦어도 현황을 남길 수 있게
            self.stdout.write(local_run.start(link, local_run.read_clipboard()))
        except Exception as e:  # 링크로 열린 창은 바로 닫히므로 이유를 보여 주고 기다린다
            self.stderr.write(f"[일일루틴] 실행하지 못했습니다: {e}")
            if pause:
                input("Enter 를 누르면 닫습니다.")
            raise SystemExit(1) from None
