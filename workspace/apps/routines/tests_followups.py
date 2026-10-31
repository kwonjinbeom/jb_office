import json
import tempfile
from datetime import date, timedelta
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.core.models import ROUTINE_BRIEF_TOKEN_KEY, AppSetting

from .local_run import start
from .models import FollowUp, Routine, RoutineRun
from .views import launcher

PAGE = reverse("routines:followups")


class FollowUpTests(TestCase):
    """이어서 할 일 (2026-10-31 사용자): 터미널이 끝내지 못한 일을 남기고, 이어서 하고, 완료로."""

    def setUp(self):
        self.client.force_login(get_user_model().objects.create_user("tester", password="pw-test-1234"))
        AppSetting.set(ROUTINE_BRIEF_TOKEN_KEY, "tok")
        self.writing = Routine.objects.get(key="writing")

    def post_json(self, url, data):
        return self.client.post(url, json.dumps(data, ensure_ascii=False).encode("utf-8"),
                                content_type="application/json; charset=utf-8")

    def test_prompts_tell_claude_how_to_leave_followups(self):
        text = launcher(self.writing, date(2026, 11, 1), report="http://s/routines/report/writing/?token=tok&day=2026-11-01&via=run")
        self.assertIn("## 끝내지 못한 일 (이어서 할 일)", text)
        self.assertIn("http://s/routines/followups/new/?token=tok&source=writing&day=2026-11-01&key=writing", text)
        self.assertIn('--data-binary "@workspace/.routine/followup.json"', text)
        pc = launcher(self.writing, date(2026, 11, 1), report=True)
        self.assertIn("manage.py routine_followup new workspace/.routine/followup.json --source writing --date 2026-11-01", pc)

    def test_api_new_and_dedupe(self):
        url = reverse("routines:followup_new") + "?source=writing&day=2026-11-01&key=writing"
        self.client.logout()
        self.assertEqual(self.post_json(url + "&token=x", {"title": "a"}).status_code, 403)
        item = {"title": "T226 순천 원고 — 네이버 지도 번호 못 찾음", "why": "브라우저 잠금", "next": "1. 지도 번호 찾기\n2. 원고 저장"}
        self.assertEqual(self.post_json(url + "&token=tok", [item, {"title": "T229 11번가"}]).status_code, 200)
        self.assertEqual(self.post_json(url + "&token=tok", dict(item, next="고친 할 일")).status_code, 200)  # 같은 날 같은 제목은 고친다
        self.assertEqual(FollowUp.objects.count(), 2)
        fu = FollowUp.objects.get(title__startswith="T226")
        self.assertEqual((fu.source, fu.routine, fu.day, fu.next_steps, fu.status),
                         ("writing", self.writing, date(2026, 11, 1), "고친 할 일", "open"))
        self.assertEqual(self.client.post(url + "&token=tok", b"not json", content_type="application/json").status_code, 400)

    @patch("apps.routines.local_run.find_claude", return_value="claude")
    @patch("apps.routines.local_run.subprocess.Popen")
    def test_resume_then_report_done(self, popen, _claude):
        run = RoutineRun.record(self.writing, date(2026, 11, 1), "시작", "글쓰기 시작")
        run.report(RoutineRun.Status.FAILED, "브라우저를 못 열었다", timezone.localtime())
        res = self.client.get(PAGE)
        self.assertEqual([r.pk for r in res.context["runs"]], [run.pk])  # 확인이 필요한 실행
        self.client.post(reverse("routines:followup_promote", args=[run.pk]))
        fu = FollowUp.objects.get()
        self.assertEqual((fu.run, fu.source), (run, "writing"))
        self.assertEqual(self.client.get(PAGE).context["runs"], [])  # 올린 실행은 빠진다
        data = self.client.post(reverse("routines:followup_resume", args=[fu.pk])).json()
        self.assertTrue(data["prompt"].startswith("# 일일루틴 이어서 하기"))
        self.assertIn("브라우저를 못 열었다", data["prompt"])  # 그때 실행 기록
        self.assertIn(f"/routines/followups/{fu.pk}/report/?token=tok", data["prompt"])
        fu.refresh_from_db()
        self.assertEqual(fu.status, "running")
        with tempfile.TemporaryDirectory() as tmp, override_settings(BASE_DIR=Path(tmp)), patch("apps.routines.local_run.WINDOWS", True):
            msg = start(f"jbroutine:followup?key={data['key']}&day={data['day']}&name=x", data["prompt"])
            self.assertIn("이어서 하기", msg)
            self.assertTrue((Path(tmp) / ".routine" / f"followup-{data['key']}-{data['day']}.md").exists())
        self.assertEqual(RoutineRun.objects.count(), 1)  # 이어서 하기는 루틴 현황을 새로 만들지 않는다
        report = reverse("routines:followup_report", args=[fu.pk]) + "?token=tok"
        self.assertEqual(self.post_json(report, {"status": "실패", "note": "또 막힘", "next": "남은 것"}).status_code, 200)
        fu.refresh_from_db()
        self.assertEqual((fu.status, fu.next_steps), ("open", "남은 것"))
        self.assertEqual(self.post_json(report, {"status": "완료", "note": "원고 저장"}).status_code, 200)
        fu.refresh_from_db()
        self.assertEqual(fu.status, "done")
        self.assertIsNotNone(fu.resolved_at)
        self.assertIn("원고 저장", fu.log)
        self.assertEqual(self.client.get(PAGE).context["counts"], {"open": 0, "recheck": 0, "done": 1})

    def test_stale_running_runs_and_close(self):
        run = RoutineRun.record(self.writing, timezone.localdate(), "시작", "주제 기획")
        self.assertEqual(self.client.get(PAGE).context["runs"], [])  # 방금 소식이 있으면 아니다
        RoutineRun.objects.filter(pk=run.pk).update(updated_at=timezone.now() - timedelta(hours=4))
        runs = self.client.get(PAGE).context["runs"]
        self.assertEqual([r.pk for r in runs], [run.pk])
        self.assertIn("소식 없음", runs[0].why)
        self.client.post(reverse("routines:followup_close_run", args=[run.pk]))
        run.refresh_from_db()
        self.assertEqual(run.status, "done")
        self.assertEqual(self.client.get(PAGE).context["runs"], [])

    def test_recheck_waits_then_shows_in_check_grid(self):
        """다시 확인 (2026-10-31 사용자): 공개 전 정보는 check_on 을 달아 아래 '확인이 필요한 것' 칸에. 그날 전엔 '기다림'."""
        today = timezone.localdate()
        url = reverse("routines:followup_new") + f"?token=tok&source=writing&day={today}&key=writing"
        item = {"title": "T236 올영 블프 — 본 행사 쿠폰·할인 공개 확인", "why": "11/1 0시 공개", "next": "공식 기획전을 보고 한 편 더",
                "check_on": (today + timedelta(days=1)).isoformat()}
        self.assertEqual(self.post_json(url, item).status_code, 200)
        fu = FollowUp.objects.get()
        self.assertEqual(fu.check_on, today + timedelta(days=1))
        res = self.client.get(PAGE)
        self.assertEqual(res.context["items"], [])  # 위 '남은 일'이 아니라
        self.assertEqual([f.pk for f in res.context["rechecks"]], [fu.pk])  # 아래 칸에
        self.assertEqual(res.context["counts"]["recheck"], 1)
        self.assertContains(res, "기다림")
        self.assertEqual(self.client.get(reverse("routines:index")).context["followup_open"], 0)  # 날이 오기 전엔 세지 않는다
        FollowUp.objects.filter(pk=fu.pk).update(check_on=today)
        self.assertContains(self.client.get(PAGE), "확인할 때")
        prompt = self.client.post(reverse("routines:followup_resume", args=[fu.pk])).json()["prompt"]
        self.assertIn("다시 확인하기로 남긴 일", prompt)
        self.assertIn("## 다시 확인하는 까닭", prompt)
        self.client.post(reverse("routines:followup_add"), {"title": "빼빼로 편의점 공지", "check_on": "2026-11-02"})
        self.assertEqual(FollowUp.objects.get(title="빼빼로 편의점 공지").check_on, date(2026, 11, 2))

    def test_daily_ideas_runs_are_not_checked(self):
        ideas = Routine.objects.get(key="daily_ideas")
        run = RoutineRun.record(ideas, timezone.localdate(), "시작", "아이디어")
        run.report(RoutineRun.Status.FAILED, "검색 실패", timezone.localtime())
        self.assertEqual(self.client.get(PAGE).context["runs"], [])

    def test_prompts_ask_for_recheck(self):
        text = launcher(self.writing, date(2026, 11, 1), report=True)
        self.assertIn("나중에 다시 찾아야 할 것", text)
        self.assertIn('"check_on": "YYYY-MM-DD"', text)

    def test_page_add_edit_mark(self):
        self.client.post(reverse("routines:followup_add"), {"title": "  변환 다시  ", "source": "convert", "next_steps": "T219 다시 변환"})
        fu = FollowUp.objects.get()
        self.assertEqual((fu.title, fu.source), ("변환 다시", "convert"))
        res = self.client.get(PAGE)
        self.assertContains(res, "이어서 하기")
        self.assertContains(res, "T219 다시 변환")
        self.client.post(reverse("routines:followup_save", args=[fu.pk]), {"title": "변환 다시", "why": "사진", "next_steps": "새 할 일"})
        self.client.post(reverse("routines:followup_mark", args=[fu.pk, "drop"]))
        fu.refresh_from_db()
        self.assertEqual((fu.why, fu.next_steps, fu.status), ("사진", "새 할 일", "dropped"))
        self.assertContains(self.client.get(PAGE, {"t": "done"}), "다시 남음")
        self.client.post(reverse("routines:followup_mark", args=[fu.pk, "open"]))
        fu.refresh_from_db()
        self.assertEqual((fu.status, fu.resolved_at), ("open", None))

    def test_menu_and_index_link(self):
        from apps.core.menus import find_menu
        self.assertEqual(find_menu("routine_followups").title, "이어서 할 일")
        FollowUp.objects.create(title="남은 것", day=timezone.localdate())
        self.assertContains(self.client.get(reverse("routines:index")), "이어서 할 일 1")

    def test_pc_command(self):
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp) / "fu.json"
            f.write_text(json.dumps({"title": "PC 에 남김", "next": "할 일"}, ensure_ascii=False), encoding="utf-8")
            out = StringIO()
            call_command("routine_followup", "new", str(f), "--source", "writing", "--date", "2026-11-01", "--key", "writing", stdout=out)
            fu = FollowUp.objects.get()
            f.write_text(json.dumps({"status": "완료", "note": "끝"}, ensure_ascii=False), encoding="utf-8")
            call_command("routine_followup", "report", str(fu.pk), str(f), stdout=out)
        fu.refresh_from_db()
        self.assertEqual(fu.status, "done")
