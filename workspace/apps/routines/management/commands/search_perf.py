"""우리 글의 검색 성과 받기: python manage.py search_perf [--auth]

--auth: 처음 한 번 브라우저로 구글 동의 (콘텐츠/블로그_카페/데이터/README.md '검색 성과'). apps/routines/search_perf.py.
"""
from django.core.management.base import BaseCommand

from apps.routines import search_perf


class Command(BaseCommand):
    help = "구글 서치 콘솔에서 사이트별 최근 28일 글×검색어를 받아 workspace/.routine/perf/ 에 쓴다"

    def add_arguments(self, parser):
        parser.add_argument("--auth", action="store_true", help="처음 한 번: 브라우저에서 구글 동의를 받아 토큰을 저장")

    def handle(self, *args, **opts):
        try:
            if opts["auth"]:
                self.stdout.write(f"저장했습니다: {search_perf.authorize()}")
                return
            for site, msg in search_perf.pull():
                self.stdout.write(f"{site} · {msg}")
            self.stdout.write(f"폴더: {search_perf.out_dir()}")
        except search_perf.PerfError as e:
            self.stdout.write(f"건너뜀: {e}")
