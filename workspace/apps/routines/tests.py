import json
import tempfile
from datetime import date
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.core.models import TrashEntry
from apps.naver_writing.models import Post as NaverPost
from apps.writing.models import Post as TistoryPost

from .models import Evaluation, PromptVersion, Routine, RoutineDay, RoutineRun
from .views import capture_version, launcher, references

INDEX = reverse("routines:index")
PROMPTS = reverse("routines:prompts")
LAUNCH = reverse("routines:launch")
DRAFT = "제작 정보\n<!-- 본문 시작 -->\n# 네이버 첫 원고\n본문입니다.\n<!-- 본문 끝 -->\n태그: 하나, 둘\n소개: 짧은 소개\n"


class Login(TestCase):
    def setUp(self):
        self.client.force_login(get_user_model().objects.create_user("tester", password="pw-test-1234"))


class TempRepoTests(Login):
    """저장소 경로를 임시 폴더로 바꿔 쓰는 것 (실행 파일·원고 폴더·아이디어 JSON)."""

    def setUp(self):
        super().setUp()
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        (self.root / "ideas").mkdir()
        (self.root / "workspace").mkdir()
        paths = override_settings(REPO_ROOT=self.root, BASE_DIR=self.root / "workspace", DAILY_IDEAS_DIR=self.root / "ideas")
        paths.enable()
        self.addCleanup(paths.disable)

    def row(self, key, **params):
        return next(r for r in self.client.get(INDEX, params).context["routines"] if r.key == key)

    def test_seed_and_screen(self):
        self.assertEqual(list(Routine.objects.values_list("key", flat=True)), ["daily_ideas", "tistory", "naver", "prompt_update"])
        res = self.client.get(INDEX)
        for text in ["일일루틴", "티스토리 글쓰기", "네이버 글쓰기", "프롬프트 최신화", ">실행<", "프롬프트 복사", "미완료", "로컬 현황", 'id="rt-view"']:
            self.assertContains(res, text)
        self.assertNotContains(res, 'data-copy="#p-tistory-local"')  # 로컬 칸은 실행만

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

    def test_launcher_same_md_cloud_adds_constraints(self):
        (self.root / "ideas" / "2026-10-14.json").write_text(json.dumps({
            "date": "2026-10-14", "title": "t", "items": [dict(
                id="a1", title="지난 후보", category="tool", audience="a", problem="p", min_product="m", money_flow="f",
                channel="c", evidence="e", risk="r", first_test="t", decision="d", sources=[])]}), encoding="utf-8")
        NaverPost.objects.create(title="이미 쓴 네이버 글")
        day = date(2026, 10, 16)
        naver = Routine.objects.get(key="naver")
        local, cloud = launcher(naver, "local", day), launcher(naver, "cloud", day)
        for text in (local, cloud):
            self.assertIn("`일일루틴/프롬프트/naver.md`", text)  # 같은 프롬프트 md
            self.assertIn("체크: 쇼핑커넥트 링크는", text)
            self.assertIn("이미 쓴 네이버 글", text)
        self.assertIn("일일루틴/클라우드_제약.md", cloud)
        self.assertNotIn("클라우드_제약", local)
        self.assertIn("routine_report naver <상태>", local)
        self.assertNotIn("routine_report", cloud)
        ideas = launcher(Routine.objects.get(key="daily_ideas"), "cloud", day)
        self.assertIn("2026-10-14 · 지난 후보", ideas)
        self.assertIn("검색 표준", ideas)

    @patch("apps.routines.views.subprocess.Popen")
    def test_launch_from_server_page_opens_terminal(self, popen):
        data = {"key": "tistory", "name": "티스토리 글쓰기", "kind": "run", "day": "2026-10-16", "prompt": "# 안내문\n할 일"}
        with patch("apps.routines.views.os.name", "nt"):
            res = self.client.post(LAUNCH, data, HTTP_ORIGIN="https://jbkwon.pythonanywhere.com")
        self.assertEqual(res.status_code, 302)
        f = self.root / "workspace" / ".routine" / "tistory-2026-10-16.md"
        self.assertEqual(f.read_text(encoding="utf-8"), "# 안내문\n할 일")
        self.assertEqual(popen.call_args[0][0][-2:], ["claude", "Read workspace/.routine/tistory-2026-10-16.md and follow it exactly."])
        run = RoutineRun.objects.get()
        self.assertEqual((run.status, run.day), ("running", date(2026, 10, 16)))
        # 실서버에만 있는 루틴이면 PC DB 에 만들어 기록한다
        with patch("apps.routines.views.os.name", "nt"):
            self.client.post(LAUNCH, {**data, "key": "wordpress", "name": "워드프레스"}, HTTP_ORIGIN="http://127.0.0.1:8000")
        self.assertTrue(Routine.objects.filter(key="wordpress", name="워드프레스").exists())

    @patch("apps.routines.views.subprocess.Popen")
    def test_launch_refuses_other_sites_and_server(self, popen):
        data = {"key": "tistory", "kind": "run", "prompt": "x"}
        self.assertEqual(self.client.post(LAUNCH, data, HTTP_ORIGIN="https://evil.example").status_code, 403)
        self.assertEqual(self.client.post(LAUNCH, data).status_code, 403)  # Origin 없음
        with override_settings(IS_SERVER=True):
            self.assertEqual(self.client.post(LAUNCH, data, HTTP_ORIGIN="https://jbkwon.pythonanywhere.com").status_code, 403)
        popen.assert_not_called()

    def test_server_page_posts_to_pc(self):
        with override_settings(IS_SERVER=True):
            res = self.client.get(INDEX)
        self.assertContains(res, 'action="http://127.0.0.1:8000/routines/launch/" target="_blank"')
        self.assertContains(res, "PC 화면에서 보기")

    def test_naver_import_drafts(self):
        folder = self.root.joinpath("콘텐츠", "블로그_카페", "포스팅자동화", "네이버원고", "N01_첫원고")
        folder.mkdir(parents=True)
        (folder / "원고.md").write_text(DRAFT, encoding="utf-8")
        self.assertContains(self.client.get(reverse("naver_writing:import")), "네이버 첫 원고")
        self.client.post(reverse("naver_writing:import"), {"keys": ["N01_첫원고"]})
        post = NaverPost.objects.get(title="네이버 첫 원고")
        self.assertEqual((post.stage, post.tags, post.summary), ("temp", "하나, 둘", "짧은 소개"))


class RepoTests(Login):
    """저장소의 실제 md (일일루틴/프롬프트, 클라우드_제약) 를 쓴다."""

    def report(self, *args):
        out = StringIO()
        call_command("routine_report", *args, stdout=out)
        return out.getvalue()

    def test_report_command_and_panel(self):
        self.assertIn("ok tistory 2026-10-16 running", self.report("tistory", "시작", "사이트 최근 글 확인", "--date", "2026-10-16"))
        self.report("tistory", "대기", "티스토리 로그인 필요", "--date", "2026-10-16")
        run = RoutineRun.objects.get()
        self.assertEqual((run.status, run.step, run.log.count("\n")), ("waiting", "티스토리 로그인 필요", 1))
        res = self.client.get(INDEX, {"date": "2026-10-16"})
        self.assertContains(res, "티스토리 로그인 필요")
        self.assertContains(res, 'data-rt-refresh="15"')
        self.report("tistory", "완료", "원고 4편", "--date", "2026-10-16")
        self.report("tistory", "시작", "다시", "--date", "2026-10-16")
        self.assertEqual(RoutineRun.objects.count(), 2)

    def test_references_are_md_reads_cloud_and_data(self):
        tistory = Routine.objects.get(key="tistory")
        refs = references(tistory)
        self.assertEqual([r["kind"] for r in refs][:1], ["프롬프트"])
        labels = [r["label"] for r in refs]
        for label in ["일일루틴/프롬프트/tistory.md", "AGENTS.md", "workspace/TISTORY_WRITER.md",
                      "콘텐츠/블로그_카페/포스팅자동화/원고/README.md", "일일루틴/클라우드_제약.md", "사이트·체크 (운영 화면)"]:
            self.assertIn(label, labels)
        self.assertTrue(all(r["ok"] for r in refs))
        self.assertFalse(any("T번호" in label for label in labels))  # 쓰는 곳은 '보는 md'가 아니다

    def test_prompts_page_tabs_refs_and_versions(self):
        res = self.client.get(PROMPTS, {"r": "naver"})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context["routine"].key, "naver")
        for text in ["티스토리 글쓰기", "프롬프트 최신화", "workspace/NAVER_WRITER.md", "나의 평가", "프롬프트 이력", "v1",
                     'class="input pm-comment-in"']:
            self.assertContains(res, text)
        self.assertNotContains(res, "프롬프트 (원문)")
        self.assertNotContains(res, 'id="pm-update"')  # 갱신은 리스트의 '프롬프트 최신화'로
        self.assertEqual(PromptVersion.objects.filter(routine__key="naver").count(), 1)
        self.client.get(PROMPTS, {"r": "naver"})
        self.assertEqual(PromptVersion.objects.filter(routine__key="naver").count(), 1)  # 안 바뀌면 그대로

    def test_evaluations_feed_prompt_update_routine(self):
        tistory = Routine.objects.get(key="tistory")
        self.client.post(reverse("routines:evaluate", args=[tistory.pk]), {"day": "2026-10-15", "score": "2", "comment": "제목이 너무 길다"})
        self.client.post(reverse("routines:evaluate", args=[tistory.pk]), {"day": "2026-10-15", "score": "3", "comment": "제목이 길다"})
        self.assertEqual(Evaluation.objects.get().score, 3)  # 같은 날은 고친다
        refresh = Routine.objects.get(key="prompt_update")
        text = launcher(refresh, "local", date(2026, 10, 16))
        self.assertIn("`일일루틴/프롬프트/prompt_update.md`", text)
        self.assertIn("### 티스토리 글쓰기 — `일일루틴/프롬프트/tistory.md`", text)
        self.assertIn("2026-10-15 · 3점 [새] · 제목이 길다", text)
        self.assertIn("점검 관점: AI 글쓰기 유의점", text)
        self.assertIn("routine_report prompt_update", text)
        self.assertIn("일일루틴/클라우드_제약.md", launcher(refresh, "cloud", date(2026, 10, 16)))
        res = self.client.get(PROMPTS, {"r": "tistory"})
        self.assertEqual(res.context["new_count"], 1)
        # 프롬프트 md 가 바뀌어 새 버전이 생기면 그 전 평가는 '반영'
        v1 = PromptVersion.objects.get(routine=tistory)
        PromptVersion.objects.create(routine=tistory, number=2, sha="x", content="바뀐 프롬프트")
        self.assertEqual(self.client.get(PROMPTS, {"r": "tistory"}).context["new_count"], 0)
        self.assertIn("3점 · 제목이 길다", launcher(Routine.objects.get(key="prompt_update"), "local", date(2026, 10, 16)))
        # 그날 바뀐 프롬프트 수가 '프롬프트 최신화' 결과 (하루 1회 목표)
        with patch("apps.routines.views.capture_version"):
            row = next(r for r in self.client.get(INDEX).context["routines"] if r.key == "prompt_update")
        self.assertEqual((row.result, row.target, row.state), (2, 1, "done"))  # 가짜 v2 + 실제 md 로 돌아온 v3
        e = Evaluation.objects.get()
        self.client.post(reverse("routines:evaluation_delete", args=[e.pk]))
        self.assertFalse(Evaluation.objects.exists())
        self.assertTrue(TrashEntry.objects.filter(model_label="routines.evaluation").exists())
        self.client.post(reverse("routines:version_star", args=[v1.pk]))
        v1.refresh_from_db()
        self.assertTrue(v1.starred)
        res = self.client.get(reverse("routines:version_restore", args=[v1.pk]))
        self.assertContains(res, "v1 내용")

    def test_capture_version_when_md_changes(self):
        tistory = Routine.objects.get(key="tistory")
        v1 = capture_version(tistory)
        with patch("apps.routines.views._read", return_value="새 내용"):
            v2 = capture_version(tistory)
        self.assertEqual((v1.number, v2.number, v2.content), (1, 2, "새 내용"))

    def test_doc_only_for_referenced_md(self):
        self.assertContains(self.client.get(reverse("routines:doc", args=["workspace/TISTORY_WRITER.md"])), "티스토리")
        self.assertContains(self.client.get(reverse("routines:doc", args=["일일루틴/클라우드_제약.md"])), "클라우드")
        self.assertEqual(self.client.get(reverse("routines:doc", args=["workspace/DEPLOY.md"])).status_code, 404)
        self.assertEqual(self.client.get(reverse("routines:doc", args=["../secret.md"])).status_code, 404)

    def test_create_and_delete_to_trash(self):
        self.client.post(reverse("routines:create"), {
            "key": "wordpress", "name": "워드프레스 글쓰기", "url_name": "posts:index", "task": "원고", "output": "",
            "daily": 1, "unit": "편", "prompt_doc": "일일루틴/프롬프트/wordpress.md", "data": ["sites"], "review_focus": ""})
        new = Routine.objects.get(key="wordpress")
        self.assertEqual((new.order, new.data), (5, "sites"))
        res = self.client.get(PROMPTS, {"r": "wordpress"})
        self.assertContains(res, '<span class="badge red">없음</span>')  # md 가 아직 없음
        self.client.post(reverse("routines:delete", args=[new.pk]))
        self.assertFalse(Routine.objects.filter(key="wordpress").exists())
        self.assertTrue(TrashEntry.objects.filter(model_label="routines.routine").exists())
