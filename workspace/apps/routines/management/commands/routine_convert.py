"""변환까지 (2026-10-31 사용자): 전체 실행·여러 날의 차례 창이 글쓰기 터미널이 끝난 뒤 부른다.

    workspace/.venv/Scripts/python workspace/manage.py routine_convert "<서버 변환 주소>" all-2026-11-02-2-convert.md

서버(routines.views.convert_api)가 그날 쓴 글을 발행예정글로 옮기고 변환 안내문을 주면 .routine/<이름> 에 쓴다.
PC 의 지금 커밋(HEAD)을 함께 보내 서버에 원고가 반영될 때까지 기다린다. 끝 코드: 0 = 안내문 씀(차례 창이 변환 터미널을 연다),
3 = 변환할 글 없음, 1 = 실패 (둘 다 그 차례는 건너뛴다).
"""
import subprocess

from django.conf import settings
from django.core.management.base import BaseCommand

from apps.routines import local_run


class Command(BaseCommand):
    help = "변환까지: 서버에서 그날 변환 안내문을 받아 .routine 에 쓴다"

    def add_arguments(self, parser):
        parser.add_argument("url")
        parser.add_argument("name")

    def handle(self, url, name, **options):
        try:
            head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(settings.REPO_ROOT), capture_output=True,
                                  text=True, timeout=10).stdout.strip()
        except (OSError, subprocess.SubprocessError):
            head = ""
        code, message = local_run.fetch_convert(url, name, head)
        self.stdout.write(f"[변환] {message}")
        raise SystemExit(code)
