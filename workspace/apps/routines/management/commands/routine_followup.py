"""이어서 할 일을 PC DB 에 남기는 명령 (보고 토큰이 없을 때 — 안내문의 '끝내지 못한 일' · '끝나면').

    workspace/.venv/Scripts/python workspace/manage.py routine_followup new workspace/.routine/followup.json --source writing --date 2026-11-01 --key writing
    workspace/.venv/Scripts/python workspace/manage.py routine_followup report 12 workspace/.routine/followup-12.json

JSON 은 UTF-8: new 는 {"title", "why", "next"} (또는 목록), report 는 {"status": 완료|실패|막힘, "note", "next"}.
"""
import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.routines import followups
from apps.routines.models import FollowUp


class Command(BaseCommand):
    help = "이어서 할 일 남기기 (new) · 이어서 하기 결과 보고 (report)"

    def add_arguments(self, parser):
        parser.add_argument("action", choices=["new", "report"])
        parser.add_argument("args", nargs="+", help="new: <json> · report: <번호> <json>")
        parser.add_argument("--source", default="other")
        parser.add_argument("--date", default="")
        parser.add_argument("--key", default="")

    def _read(self, path):
        f = Path(path)
        if not f.is_absolute():
            f = Path(settings.REPO_ROOT) / f
        try:
            return f.read_text(encoding="utf-8-sig")
        except OSError as e:
            raise CommandError(f"파일을 못 읽었습니다: {e}") from None

    def handle(self, action, args, source, date, key, **options):
        try:
            if action == "new":
                saved = followups.add_items(followups._items(self._read(args[0])), source, followups._day(date), key)
                self.stdout.write(f"ok {len(saved)} " + " ".join(f"#{f.pk}" for f in saved))
            else:
                if len(args) < 2 or not args[0].isdigit():
                    raise CommandError("report <번호> <json>")
                fu = FollowUp.objects.filter(pk=int(args[0])).first()
                if fu is None:
                    raise CommandError(f"#{args[0]} 이 없습니다 (PC DB)")
                followups.apply_report(fu, json.loads(self._read(args[1])))
                self.stdout.write(f"ok #{fu.pk} {fu.status}")
        except ValueError as e:
            raise CommandError(str(e)) from None
