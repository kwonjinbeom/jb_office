"""사이트별·글별 조회수 받기: python manage.py site_views [--setup] [--days N]

--setup: GA4 속성이 없는 사이트에 속성을 만들고 측정 ID 와 붙일 코드를 보여 준다 (콘텐츠/블로그_카페/데이터/README.md '조회수').
인증은 search_perf --auth 와 같다. apps/routines/site_views.py.
"""
from django.core.management.base import BaseCommand

from apps.routines import site_views


class Command(BaseCommand):
    help = "GA4 에서 사이트별 최근 N일 글별 조회수·날짜별 조회수·유입 경로를 받아 workspace/.routine/perf/ 에 쓴다"

    def add_arguments(self, parser):
        parser.add_argument("--setup", action="store_true", help="GA4 속성이 없는 사이트에 속성을 만들고 측정 ID 를 보여 준다")
        parser.add_argument("--days", type=int, default=site_views.DAYS, help="최근 며칠 (기본 28)")

    def handle(self, *args, **opts):
        try:
            if opts["setup"]:
                for h, mid, new in site_views.setup():
                    self.stdout.write(f"\n{h} · {mid} ({'새로 만듦' if new else '이미 있음'})")
                    self.stdout.write(site_views.snippet(mid))
                return
            for h, line, top in site_views.pull(days=opts["days"]):
                self.stdout.write(f"\n{h} · {line}")
                for views, users, path, title in top:
                    self.stdout.write(f"  {views:>6}  {users:>5}  {title or path}")
            self.stdout.write(f"\n폴더: {site_views.search_perf.out_dir()}")
        except site_views.PerfError as e:
            self.stdout.write(f"건너뜀: {e}")
