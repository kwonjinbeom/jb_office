"""공공 데이터 받아 쌓기: python manage.py collect_data [--only 축제,분양]

글쓰기 루틴 메인이 기획 전에 한 번 돌린다 (일일루틴/프롬프트/writing.md '데이터 폴더'). apps/routines/datafeeds.py.
"""
from django.core.management.base import BaseCommand

from apps.routines import datafeeds


class Command(BaseCommand):
    help = "공공 API(관광공사 축제·청약홈·KOBIS·OpenDART·FRED)를 받아 콘텐츠/블로그_카페/데이터/*.csv 에 쌓는다"

    def add_arguments(self, parser):
        parser.add_argument("--only", default="", help="쉼표로 출처 이름 (축제,분양,박스오피스,증권신고서,미국지수)")

    def handle(self, *args, **opts):
        only = {x.strip() for x in opts["only"].split(",") if x.strip()} or None
        results = datafeeds.collect(only=only)
        self.stdout.write(" · ".join(f"{name} {msg}" for name, msg in results))
        self.stdout.write(f"폴더: {datafeeds.data_dir()}")
