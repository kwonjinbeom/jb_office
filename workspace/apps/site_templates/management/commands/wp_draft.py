"""변환본을 워드프레스 초안으로 올리기 (PC 에서, 변환 안내문이 글마다 실행한다 — site_templates.wp_rest).

    workspace/.venv/Scripts/python.exe workspace/manage.py wp_draft "<서버 api/wp/<번호>/?token=… 주소>"
    workspace/.venv/Scripts/python.exe workspace/manage.py wp_draft --check     # 비밀번호·연결 확인
    workspace/.venv/Scripts/python.exe workspace/manage.py wp_draft --restyle "<api/wp 주소>"  # 올린 글 본문만 지금 글 모양으로

workspace/.env 에 WP_USER · WP_APP_PASSWORD 가 없으면 건너뛴다 (변환은 그대로 끝난다).
"""
import urllib.error

from django.core.management.base import BaseCommand, CommandError

from apps.site_templates import wp_rest


class Command(BaseCommand):
    help = "워드프레스 초안 올리기: <서버 api/wp 주소> 또는 --check"

    def add_arguments(self, parser):
        parser.add_argument("url", nargs="?", default="")
        parser.add_argument("--check", action="store_true")
        parser.add_argument("--restyle", action="store_true", help="이미 올린 글(발행 포함)의 본문만 지금 글 모양으로 다시 그린다")

    def handle(self, url, check, restyle=False, **options):
        conf = wp_rest.config()
        if conf is None:
            self.stdout.write("건너뜀 · workspace/.env 에 WP_USER · WP_APP_PASSWORD 가 없습니다 (사이트_꾸미기.md '초안 자동 올리기')")
            return
        client = wp_rest.Client(*conf)
        try:
            if check:
                me = client.me()
                cats = client.call("GET", "/categories?per_page=100&hide_empty=false")
                self.stdout.write(f"ok · {conf[0]} · {me.get('name')} ({', '.join(me.get('roles', []))}) · "
                                  f"카테고리 {len(cats)}개 · unfiltered_html {me.get('capabilities', {}).get('unfiltered_html', False)}")
                return
            if not url:
                raise CommandError("서버 api/wp 주소를 주거나 --check")
            if restyle:
                self.stdout.write(wp_rest.restyle(url, client))
                return
            self.stdout.write(wp_rest.draft(url, client, log=self.stdout.write))
        except wp_rest.WPError as e:
            raise CommandError(f"워드프레스가 거절했습니다: {e}") from None
        except (urllib.error.URLError, OSError) as e:
            raise CommandError(f"연결하지 못했습니다: {e}") from None
