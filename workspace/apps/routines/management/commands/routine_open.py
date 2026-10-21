"""일일루틴 '실행' 링크(jbroutine:)를 받아 PC 에서 claude 터미널을 여는 명령. Windows 가 링크를 열 때 부른다.

    workspace/.venv/Scripts/python workspace/manage.py routine_open --pause "jbroutine:run?key=writing&day=2026-10-16"

안내문은 화면이 클립보드에 복사해 둔 것을 읽는다. 등록은 workspace/routine_link.bat (run.bat 이 부른다).
열 때마다 먼저 git pull --ff-only 로 PC 코드를 main 최신으로 맞추고, 바뀌었으면 새 코드로 이 명령을 다시 부른다.
"""
import subprocess
import sys

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand

from apps.routines import local_run


class Command(BaseCommand):
    help = "일일루틴 실행 링크로 claude 터미널 열기 (안내문은 클립보드에서)"

    def add_arguments(self, parser):
        parser.add_argument("link")
        parser.add_argument("--pause", action="store_true", help="실패하면 창을 닫기 전에 기다린다 (링크로 열린 창)")
        parser.add_argument("--no-pull", action="store_true", help="git pull 을 건너뛴다 (최신으로 맞춘 뒤 새 코드로 다시 부를 때)")

    def handle(self, link, pause, no_pull, **options):
        if not no_pull:
            changed, error = local_run.pull_latest()
            if error:  # 네트워크·로컬 변경·다른 브랜치 등. 알리고 지금 코드로 계속한다
                self.stderr.write(f"[일일루틴] PC 코드가 최신이 아닙니다 (git pull 실패: {error}). 지금 코드로 실행합니다.")
                if pause:
                    input("Enter 를 누르면 계속합니다.")
            elif changed:  # 이 프로세스는 옛 코드를 이미 읽었으므로 새 코드로 다시 부른다
                again = [sys.executable, str(settings.BASE_DIR / "manage.py"), "routine_open", link, "--no-pull"]
                raise SystemExit(subprocess.call(again + (["--pause"] if pause else [])))
        try:
            call_command("migrate", interactive=False, verbosity=0)  # PC DB 가 코드보다 늦어도 현황을 남길 수 있게
            self.stdout.write(local_run.start(link, local_run.read_clipboard()))
        except Exception as e:  # 링크로 열린 창은 바로 닫히므로 이유를 보여 주고 기다린다
            self.stderr.write(f"[일일루틴] 실행하지 못했습니다: {e}")
            if pause:
                input("Enter 를 누르면 닫습니다.")
            raise SystemExit(1) from None
