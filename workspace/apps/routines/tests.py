import json
import tempfile
from datetime import date
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.naver_writing.models import Post as NaverPost
from apps.writing.models import Post as TistoryPost

from .models import Routine, RoutineDay, RoutineRun
from .views import render_prompt

INDEX = reverse("routines:index")
DRAFT = "제작 정보\n<!-- 본문 시작 -->\n# 네이버 첫 원고\n본문입니다.\n<!-- 본문 끝 -->\n태그: 하나, 둘\n소개: 짧은 소개\n"


class RoutineTests(TestCase):
    def setUp(self):
        self.client.force_login(get_user_model().objects.create_user("tester", password="pw-test-1234"))
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        (self.root / "ideas").mkdir()
        paths = override_settings(REPO_ROOT=self.root, BASE_DIR=self.root / "workspace", DAILY_IDEAS_DIR=self.root / "ideas")
        paths.enable()
        self.addCleanup(paths.disable)
        (self.root / "workspace").mkdir()

    def row(self, key, **params):
        return next(r for r in self.client.get(INDEX, params).context["routines"] if r.key == key)

    def test_seed_and_screen(self):
        self.assertEqual(list(Routine.objects.values_list("key", flat=True)), ["daily_ideas", "tistory", "naver"])
        res = self.client.get(INDEX)
        self.assertEqual(res.status_code, 200)
        for text in ["일일루틴", "일일 아이디어", "티스토리 글쓰기", "네이버 글쓰기", "터미널 실행", "프롬프트 복사", "미완료", "일별", "월별"]:
            self.assertContains(res, text)

    def test_results_count_and_edit(self):
        TistoryPost.objects.create(title="오늘 원고")
        tistory = Routine.objects.get(key="tistory")
        today = timezone.localdate().isoformat()
        r = self.row("tistory")
        self.assertEqual((r.result, r.target, r.state), (1, 4, "todo"))
        self.client.post(reverse("routines:count", args=[tistory.pk]), {"day": today, "value": "4"})
        r = self.row("tistory")
        self.assertEqual((r.result, r.state, r.fixed), (4, "done", True))
        self.client.post(reverse("routines:count", args=[tistory.pk]), {"day": today, "value": ""})
        self.assertFalse(RoutineDay.objects.exists())
        self.assertEqual(self.row("tistory", month=today[:7]).target % 4, 0)  # 월별: 하루 양 × 지난 날 수

    def test_prompts_differ_by_mode(self):
        (self.root / "ideas" / "2026-10-14.json").write_text(json.dumps({
            "date": "2026-10-14", "title": "t", "items": [dict(
                id="a1", title="지난 후보", category="tool", audience="a", problem="p", min_product="m", money_flow="f",
                channel="c", evidence="e", risk="r", first_test="t", decision="d", sources=[])]}), encoding="utf-8")
        NaverPost.objects.create(title="이미 쓴 네이버 글")
        day = date(2026, 10, 16)
        naver = Routine.objects.get(key="naver")
        local, cloud = render_prompt(naver, "local", day), render_prompt(naver, "cloud", day)
        self.assertIn("black_lukey", local)
        self.assertIn("체크: 쇼핑커넥트 링크는", local)
        self.assertIn("직접 확인", local)
        self.assertNotIn("이미 쓴 네이버 글", local)
        self.assertIn("이미 쓴 네이버 글", cloud)  # 클라우드는 사이트 대신 이미 있는 글 목록
        self.assertIn("PR", cloud)
        ideas = render_prompt(Routine.objects.get(key="daily_ideas"), "cloud", day)
        self.assertIn("2026-10-14 · 지난 후보", ideas)
        self.assertIn("검색 표준", ideas)

    @patch("apps.routines.views.subprocess.Popen")
    def test_run_local_writes_prompt_and_opens_terminal(self, popen):
        tistory = Routine.objects.get(key="tistory")
        with patch("apps.routines.views.os.name", "nt"):
            self.client.post(reverse("routines:run", args=[tistory.pk]), {"day": "2026-10-16"})
        f = self.root / "workspace" / ".routine" / "tistory-2026-10-16.md"
        self.assertIn("로컬 PC", f.read_text(encoding="utf-8"))
        args = popen.call_args[0][0]
        self.assertEqual(args[-2:], ["claude", "Read workspace/.routine/tistory-2026-10-16.md and follow it exactly."])

    @patch("apps.routines.views.subprocess.Popen")
    def test_run_local_blocked_on_server(self, popen):
        with override_settings(IS_SERVER=True):
            res = self.client.post(reverse("routines:run", args=[Routine.objects.first().pk]), follow=True)
        popen.assert_not_called()
        self.assertContains(res, "PC 에서 띄운 서버에서만")
        self.assertNotContains(res, "새 터미널에서 claude 로 시작")  # 터미널 실행 버튼 없음

    def test_naver_import_drafts(self):
        folder = self.root.joinpath("콘텐츠", "블로그_카페", "포스팅자동화", "네이버원고", "N01_첫원고")
        folder.mkdir(parents=True)
        (folder / "원고.md").write_text(DRAFT, encoding="utf-8")
        self.assertContains(self.client.get(reverse("naver_writing:import")), "네이버 첫 원고")
        self.client.post(reverse("naver_writing:import"), {"keys": ["N01_첫원고"]})
        post = NaverPost.objects.get(title="네이버 첫 원고")
        self.assertEqual((post.stage, post.tags, post.summary), ("temp", "하나, 둘", "짧은 소개"))


class RoutineReportTests(TestCase):
    """로컬 현황(routine_report)·프롬프트 관리·md 보기. 저장소 실제 md 를 쓴다."""

    def setUp(self):
        self.client.force_login(get_user_model().objects.create_user("tester", password="pw-test-1234"))

    def report(self, *args):
        from io import StringIO

        from django.core.management import call_command
        out = StringIO()
        call_command("routine_report", *args, stdout=out)
        return out.getvalue()

    def test_report_command_and_panel(self):
        self.assertIn("ok tistory 2026-10-16 running", self.report("tistory", "시작", "사이트 최근 글 확인", "--date", "2026-10-16"))
        self.report("tistory", "대기", "티스토리 로그인 필요", "--date", "2026-10-16")
        run = RoutineRun.objects.get()
        self.assertEqual((run.status, run.step, run.log.count("\n")), ("waiting", "티스토리 로그인 필요", 1))
        res = self.client.get(INDEX, {"date": "2026-10-16"})
        self.assertContains(res, "로컬 현황")
        self.assertContains(res, "티스토리 로그인 필요")
        self.assertContains(res, 'data-rt-refresh="15"')  # 끝나지 않은 기록이 있으면 새로고침
        self.report("tistory", "완료", "원고 4편", "--date", "2026-10-16")
        self.report("tistory", "시작", "다시", "--date", "2026-10-16")
        self.assertEqual(RoutineRun.objects.count(), 2)  # 끝난 뒤 '시작'은 새 기록

    def test_local_prompt_gets_report_block(self):
        day = date(2026, 10, 16)
        tistory = Routine.objects.get(key="tistory")
        self.assertIn("routine_report tistory <상태>", render_prompt(tistory, "local", day))
        self.assertNotIn("routine_report", render_prompt(tistory, "cloud", day))
        res = self.client.get(INDEX)
        self.assertContains(res, 'id="rt-view"')

    def test_prompts_page_lists_md_reads_only(self):
        res = self.client.get(reverse("routines:prompts"))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "workspace/TISTORY_WRITER.md")
        self.assertContains(res, "workspace/NAVER_WRITER.md")
        self.assertContains(res, "시장조사/00_아이디어_조사방법.md")
        self.assertNotContains(res, "T번호_짧은이름/원고.md</a>")  # 쓰는 곳은 '보는 md'가 아니다
        self.assertNotContains(res, '<span class="badge red">없음</span>')
        self.assertContains(res, "프롬프트 관리")

    def test_doc_only_for_referenced_md(self):
        self.assertContains(self.client.get(reverse("routines:doc", args=["workspace/TISTORY_WRITER.md"])), "티스토리")
        self.assertEqual(self.client.get(reverse("routines:doc", args=["workspace/DEPLOY.md"])).status_code, 404)
        self.assertEqual(self.client.get(reverse("routines:doc", args=["../secret.md"])).status_code, 404)

    def test_create_and_delete_to_trash(self):
        from apps.core.models import TrashEntry
        self.client.post(reverse("routines:create"), {
            "key": "wordpress", "name": "워드프레스 글쓰기", "url_name": "writing:list", "task": "원고", "output": "",
            "daily": 1, "unit": "편", "prompt_local": "로컬 {날짜}", "prompt_cloud": "클라우드 {날짜}"})
        new = Routine.objects.get(key="wordpress")
        self.assertEqual(new.order, 4)
        self.client.post(reverse("routines:delete", args=[new.pk]))
        self.assertFalse(Routine.objects.filter(key="wordpress").exists())
        self.assertTrue(TrashEntry.objects.filter(model_label="routines.routine").exists())
        self.assertEqual(self.client.get(INDEX).status_code, 200)
