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

from .models import Routine, RoutineDay
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
        self.assertNotContains(res, "터미널 실행")

    def test_naver_import_drafts(self):
        folder = self.root.joinpath("콘텐츠", "블로그_카페", "포스팅자동화", "네이버원고", "N01_첫원고")
        folder.mkdir(parents=True)
        (folder / "원고.md").write_text(DRAFT, encoding="utf-8")
        self.assertContains(self.client.get(reverse("naver_writing:import")), "네이버 첫 원고")
        self.client.post(reverse("naver_writing:import"), {"keys": ["N01_첫원고"]})
        post = NaverPost.objects.get(title="네이버 첫 원고")
        self.assertEqual((post.stage, post.tags, post.summary), ("temp", "하나, 둘", "짧은 소개"))
