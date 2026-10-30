"""주제 겹침 검사: python manage.py check_overlap <기획표 경로 | 날짜> [--words 낱말 …]

기획표(주제기획/<날짜>.md)의 슬롯마다 '- 대상:' 낱말을 지난 원고 제목·폴더 이름에서 찾는다 (apps/routines/overlap.py).
21일 안 겹침을 '반복 점검'에 적지 않았거나 대상 줄이 없으면 실패(종료 코드 1). --words 는 기획표 없이 낱말만 (작가·커스텀 글).
"""
from datetime import date
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.routines import overlap
from apps.writing import drafts


class Command(BaseCommand):
    help = "기획표의 대상 낱말이 지난 원고(21일 안)와 겹치는지 찾는다"

    def add_arguments(self, parser):
        parser.add_argument("plan", nargs="?", help="기획표 경로 또는 날짜 (2026-10-31 → 주제기획/2026-10-31.md)")
        parser.add_argument("--words", nargs="+", help="기획표 없이 낱말로만 찾기")
        parser.add_argument("--skip", nargs="*", default=[], help="뺄 T번호 (쓰고 있는 글 자신)")

    def handle(self, *args, **opts):
        if opts["words"]:
            hits = overlap.find(opts["words"], date.today(), set(opts["skip"]))
            for h in hits[:10]:
                self.stdout.write(f"{h.code} ({h.day}, {h.days}일 전) {h.title}")
            if not hits:
                self.stdout.write("겹침 없음")
            if any(h.days <= overlap.WINDOW_DAYS for h in hits):
                raise CommandError(f"{overlap.WINDOW_DAYS}일 안에 같은 대상의 원고가 있다")
            return
        if not opts["plan"]:
            raise CommandError("기획표 경로나 날짜, 또는 --words 를 준다")
        path = Path(opts["plan"])
        if not path.is_file():
            path = drafts.drafts_dir().parent / "주제기획" / f"{opts['plan']}.md"
        if not path.is_file():
            raise CommandError(f"기획표가 없다: {opts['plan']}")
        slots = overlap.check_plan(path)
        for line in overlap.report(slots):
            self.stdout.write(line)
        blocked = [s.code for s in slots if s.blocked]
        if blocked:
            raise CommandError(f"막힌 슬롯 {len(blocked)}개: {', '.join(blocked)} — 다음 후보로 바꾸거나 대상 줄을 채운 뒤 다시 돌린다")
