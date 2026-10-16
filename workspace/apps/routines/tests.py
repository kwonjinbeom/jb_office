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

from .models import Evaluation, PromptVersion, Routine, RoutineDay, RoutinePick, RoutineRun
from .local_run import parse_link, start
from .views import capture_version, launcher, references

INDEX = reverse("routines:index")
PROMPTS = reverse("routines:prompts")
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
        self.assertEqual(list(Routine.objects.values_list("key", flat=True)), ["daily_ideas", "writing", "prompt_update"])
        res = self.client.get(INDEX)
        for text in ["일일루틴", "글쓰기", "프롬프트 최신화", ">실행<", "프롬프트 복사", "미완료", "로컬 현황", 'id="rt-view"',
                     ">전체 실행<", 'id="rt-picker"', "쓸 분류"]:
            self.assertContains(res, text)
        self.assertNotContains(res, 'data-copy="#p-writing-local"')  # 로컬 칸은 실행만
        self.assertTrue(Routine.all_objects.filter(key="naver", deleted_at__isnull=False).exists())  # 네이버 글쓰기 루틴은 휴지통

    def test_results_count_and_edit(self):
        TistoryPost.objects.create(title="오늘 원고")
        NaverPost.objects.create(title="오늘 네이버 원고")  # 글쓰기는 두 글 표를 합쳐 센다
        tistory = Routine.objects.get(key="writing")
        today = timezone.localdate().isoformat()
        r = self.row("writing")
        self.assertEqual((r.result, r.target, r.state), (2, 11, "todo"))  # 목표 = 그날 고른 편수 (기본 11)
        self.client.post(reverse("routines:count", args=[tistory.pk]), {"day": today, "value": "11"})
        r = self.row("writing")
        self.assertEqual((r.result, r.state, r.fixed), (11, "done", True))
        self.client.post(reverse("routines:count", args=[tistory.pk]), {"day": today, "value": ""})
        self.assertFalse(RoutineDay.objects.exists())

    def test_launcher_same_md_cloud_adds_constraints(self):
        (self.root / "ideas" / "2026-10-14.json").write_text(json.dumps({
            "date": "2026-10-14", "title": "t", "items": [dict(
                id="a1", title="지난 후보", category="tool", audience="a", problem="p", min_product="m", money_flow="f",
                channel="c", evidence="e", risk="r", first_test="t", decision="d", sources=[])]}), encoding="utf-8")
        NaverPost.objects.create(title="이미 쓴 네이버 글")
        day = date(2026, 10, 16)
        naver = Routine.objects.get(key="writing")
        local, cloud = launcher(naver, "local", day), launcher(naver, "cloud", day)
        for text in (local, cloud):
            self.assertIn("`일일루틴/프롬프트/writing.md`", text)  # 같은 프롬프트 md
            self.assertIn("### 오늘 쓸 분류", text)
            self.assertIn("체크: 쇼핑커넥트 링크는", text)
            self.assertIn("이미 쓴 네이버 글", text)
        self.assertIn("일일루틴/클라우드_제약.md", cloud)
        self.assertNotIn("클라우드_제약", local)
        self.assertIn("routine_report writing <상태>", local)
        self.assertNotIn("routine_report", cloud)
        ideas = launcher(Routine.objects.get(key="daily_ideas"), "cloud", day)
        self.assertIn("2026-10-14 · 지난 후보", ideas)
        self.assertIn("검색 표준", ideas)

    @patch("apps.routines.local_run.WINDOWS", True)
    @patch("apps.routines.local_run.subprocess.Popen")
    def test_link_opens_terminal_with_clipboard_prompt(self, popen):
        link = "jbroutine:run?key=writing&day=2026-10-16&name=%EA%B8%80%EC%93%B0%EA%B8%B0"
        with patch("apps.routines.local_run.read_clipboard", return_value="# 일일루틴 · 글쓰기\r\n할 일"):
            call_command("routine_open", link, stdout=StringIO())
        f = self.root / "workspace" / ".routine" / "writing-2026-10-16.md"
        conf = json.loads((self.root / "workspace" / ".routine" / "settings.json").read_text(encoding="utf-8"))
        self.assertIn("Bash(git push *)", conf["permissions"]["allow"])
        self.assertIn("AskUserQuestion", conf["permissions"]["deny"])  # 방법·선택은 묻지 않는다
        self.assertEqual(f.read_text(encoding="utf-8"), "# 일일루틴 · 글쓰기\n할 일")
        args = popen.call_args[0][0]
        self.assertEqual(args[args.index("claude") + 1], "workspace/.routine/writing-2026-10-16.md 파일을 읽고 그대로 진행해.")
        self.assertIn("--settings", args)
        self.assertIn("한국어", args[args.index("--append-system-prompt") + 1])
        run = RoutineRun.objects.get()
        self.assertEqual((run.status, run.day), ("running", date(2026, 10, 16)))
        # 실서버에만 있는 루틴이면 PC DB 에 만들어 기록한다 (브라우저가 끝에 / 를 붙여도 된다)
        start("jbroutine:run/?key=wordpress&day=2026-10-16&name=%EC%9B%8C%EB%93%9C%ED%94%84%EB%A0%88%EC%8A%A4", "# 일일루틴 · 워드프레스")
        self.assertTrue(Routine.objects.filter(key="wordpress", name="워드프레스").exists())

    @patch("apps.routines.local_run.subprocess.Popen")
    def test_link_refuses_bad_link_or_clipboard(self, popen):
        for link in ["http://evil.example/?key=writing", "jbroutine:rm?key=writing", "jbroutine:run?key=../x"]:
            with self.assertRaises(ValueError):
                parse_link(link)
        with self.assertRaises(ValueError):  # 클립보드가 안내문이 아니면 열지 않는다
            start("jbroutine:run?key=writing&day=2026-10-16", "아무 글")
        with patch("apps.routines.local_run.read_clipboard", return_value="아무 글"), self.assertRaises(SystemExit):
            call_command("routine_open", "jbroutine:run?key=writing", stdout=StringIO(), stderr=StringIO())
        popen.assert_not_called()

    def test_run_button_copies_and_opens_link(self):
        with override_settings(IS_SERVER=True):
            res = self.client.get(INDEX)
        self.assertContains(res, '<form class="rt-launch"><input type="hidden" name="key" value="writing">')
        self.assertNotContains(res, "/routines/launch/")  # PC 서버로 보내지 않는다
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
        self.assertIn("ok writing 2026-10-16 running", self.report("writing", "시작", "사이트 최근 글 확인", "--date", "2026-10-16"))
        self.report("writing", "대기", "티스토리 로그인 필요", "--date", "2026-10-16")
        run = RoutineRun.objects.get()
        self.assertEqual((run.status, run.step, run.log.count("\n")), ("waiting", "티스토리 로그인 필요", 1))
        res = self.client.get(INDEX, {"date": "2026-10-16"})
        self.assertContains(res, "티스토리 로그인 필요")
        self.assertContains(res, 'data-rt-refresh="15"')
        self.report("writing", "완료", "원고 4편", "--date", "2026-10-16")
        self.report("writing", "시작", "다시", "--date", "2026-10-16")
        self.assertEqual(RoutineRun.objects.count(), 2)

    def test_references_are_md_reads_cloud_and_data(self):
        tistory = Routine.objects.get(key="writing")
        refs = references(tistory)
        self.assertEqual([r["kind"] for r in refs][:1], ["프롬프트"])
        labels = [r["label"] for r in refs]
        for label in ["일일루틴/프롬프트/writing.md", "AGENTS.md", "workspace/TISTORY_WRITER.md", "일일루틴/분류변경/README.md", "오늘 쓸 분류",
                      "콘텐츠/블로그_카페/포스팅자동화/원고/README.md", "일일루틴/클라우드_제약.md", "사이트·체크 (운영 화면)"]:
            self.assertIn(label, labels)
        self.assertTrue(all(r["ok"] for r in refs))
        self.assertFalse(any("T번호" in label for label in labels))  # 쓰는 곳은 '보는 md'가 아니다

    def test_prompts_page_tabs_refs_and_versions(self):
        res = self.client.get(PROMPTS, {"r": "writing"})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context["routine"].key, "writing")
        for text in ["글쓰기", "프롬프트 최신화", "workspace/TISTORY_WRITER.md", "나의 평가", "프롬프트 이력", "v1",
                     'class="input pm-comment-in"']:
            self.assertContains(res, text)
        self.assertNotContains(res, "프롬프트 (원문)")
        self.assertNotContains(res, 'id="pm-update"')  # 갱신은 리스트의 '프롬프트 최신화'로
        self.assertEqual(PromptVersion.objects.filter(routine__key="writing").count(), 1)
        self.client.get(PROMPTS, {"r": "writing"})
        self.assertEqual(PromptVersion.objects.filter(routine__key="writing").count(), 1)  # 안 바뀌면 그대로

    def test_evaluations_feed_prompt_update_routine(self):
        tistory = Routine.objects.get(key="writing")
        self.client.post(reverse("routines:evaluate", args=[tistory.pk]), {"day": "2026-10-15", "score": "2", "comment": "제목이 너무 길다"})
        self.client.post(reverse("routines:evaluate", args=[tistory.pk]), {"day": "2026-10-15", "score": "3", "comment": "제목이 길다"})
        self.assertEqual(Evaluation.objects.get().score, 3)  # 같은 날은 고친다
        refresh = Routine.objects.get(key="prompt_update")
        text = launcher(refresh, "local", date(2026, 10, 16))
        self.assertIn("`일일루틴/프롬프트/prompt_update.md`", text)
        self.assertIn("### 글쓰기 — `일일루틴/프롬프트/writing.md`", text)
        self.assertIn("2026-10-15 · 3점 [새] · 제목이 길다", text)
        self.assertIn("점검 관점: AI 글쓰기 유의점", text)
        self.assertIn("routine_report prompt_update", text)
        self.assertIn("일일루틴/클라우드_제약.md", launcher(refresh, "cloud", date(2026, 10, 16)))
        res = self.client.get(PROMPTS, {"r": "writing"})
        self.assertEqual(res.context["new_count"], 1)
        # 프롬프트 md 가 바뀌어 새 버전이 생기면 그 전 평가는 '반영'
        v1 = PromptVersion.objects.get(routine=tistory)
        PromptVersion.objects.create(routine=tistory, number=2, sha="x", content="바뀐 프롬프트")
        self.assertEqual(self.client.get(PROMPTS, {"r": "writing"}).context["new_count"], 0)
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
        tistory = Routine.objects.get(key="writing")
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


class WritingPickTests(Login):
    """글쓰기: 그날 쓸 분류 (기본 광고 6 · 판매 3 · IT/AI 2), 고르기·다시 뽑기·기본값, 전체 실행."""

    def setUp(self):
        super().setUp()
        self.writing = Routine.objects.get(key="writing")
        self.url = reverse("routines:picks", args=[self.writing.pk])

    def by_section(self, picks):
        from apps.blog_types.models import Category
        out = {}
        for sel, n in picks.items():
            name = Category.objects.get(pk=sel[1:]).section.name
            out[name] = out.get(name, 0) + n
        return out

    def test_default_mix_is_stable_for_the_day(self):
        from .views import default_picks
        a, b = default_picks(date(2026, 10, 16)), default_picks(date(2026, 10, 16))
        self.assertEqual(a, b)
        self.assertEqual(self.by_section(a), {"광고 수익 (조회수)": 6, "판매 수익 (커넥트)": 3, "IT/AI": 2})
        self.assertEqual(len(a), 11)  # 중분류가 넉넉하면 모두 다른 중분류

    def test_save_reroll_default(self):
        from apps.blog_types.models import Category, PostType
        it = Category.objects.get(section__name="IT/AI", name="AI 도구·활용")
        t = PostType.objects.first()
        self.client.post(self.url, {"day": "2026-10-16", f"n_{it.sel}": "3", f"n_{t.sel}": "1", "n_c999": "x", "n_g1": "2"})
        pick = RoutinePick.objects.get()
        self.assertEqual(pick.picks, {it.sel: 3, t.sel: 1})
        text = launcher(self.writing, "local", date(2026, 10, 16))
        self.assertIn("(총 4편 · 사용자가 고른 분류)", text)
        self.assertIn("- IT/AI > AI 도구·활용 — 3편", text)
        res = self.client.get(INDEX, {"date": "2026-10-16"})
        row = next(r for r in res.context["routines"] if r.key == "writing")
        self.assertEqual(row.target, 4)
        self.assertTrue(res.context["picker"]["custom"])
        self.client.post(self.url, {"day": "2026-10-16", "action": "reroll"})
        self.assertEqual(sum(RoutinePick.objects.get().picks.values()), 11)
        self.client.post(self.url, {"day": "2026-10-16", "action": "default"})
        self.assertFalse(RoutinePick.objects.exists())

    @patch("apps.routines.local_run.subprocess.Popen")
    def test_launch_all_runs_every_routine_in_one_terminal(self, popen):
        res = self.client.get(INDEX, {"date": "2026-10-16"})
        text = res.context["all_prompt"]
        self.assertIn("1. 일일 아이디어 → 2. 글쓰기 → 3. 프롬프트 최신화", text)
        self.assertEqual(text.count("## 진행 보고"), 3)
        with tempfile.TemporaryDirectory() as tmp, override_settings(BASE_DIR=Path(tmp)), patch("apps.routines.local_run.WINDOWS", True):
            start(f"jbroutine:all?key=all&day=2026-10-16&keys={res.context['all_keys']}", text)
            self.assertTrue((Path(tmp) / ".routine" / "all-2026-10-16.md").is_file())
        self.assertEqual(popen.call_count, 1)
        self.assertEqual(sorted(RoutineRun.objects.values_list("routine__key", flat=True)), ["daily_ideas", "prompt_update", "writing"])


class ClassChangeTests(TestCase):
    """AI 가 남긴 일일루틴/분류변경/*.json 을 글 분류에 반영 (중·소 추가·이름, 대분류는 안 고침, 한 번만)."""

    def test_sync_adds_and_renames_once(self):
        from apps.blog_types import changes
        from apps.blog_types.models import Category, ClassChange, PostType, Section
        self.assertEqual(list(Section.objects.get(name="IT/AI").categories.values_list("name", flat=True)),
                         ["AI 도구·활용", "개발·코딩", "IT 소식·제품"])
        with tempfile.TemporaryDirectory() as tmp, override_settings(REPO_ROOT=Path(tmp)):
            folder = Path(tmp) / "일일루틴" / "분류변경"
            folder.mkdir(parents=True)
            (folder / "2026-10-17_ai.json").write_text(json.dumps({"reason": "AI 요금제 글이 늘어", "changes": [
                {"op": "add", "parent": "IT/AI > AI 도구·활용", "name": "요금제·무료 범위 비교"},
                {"op": "add", "parent": "IT/AI", "name": "보안·개인정보", "question": "이거 안전한가?"},
                {"op": "rename", "path": "IT/AI > C IT 소식·제품", "to": "IT 소식·신제품"},
                {"op": "rename", "path": "IT/AI", "to": "바꾸면 안 됨"},
            ]}, ensure_ascii=False), encoding="utf-8")
            self.assertEqual(changes.sync(), 1)
            self.assertEqual(changes.sync(), 0)  # 같은 파일은 한 번만
        self.assertTrue(PostType.objects.filter(name="요금제·무료 범위 비교", category__name="AI 도구·활용").exists())
        new = Category.objects.get(name="보안·개인정보")
        self.assertEqual((new.code, new.section.name), ("D", "IT/AI"))
        self.assertTrue(Category.objects.filter(name="IT 소식·신제품").exists())
        self.assertTrue(Section.objects.filter(name="IT/AI").exists())  # 대분류는 그대로
        log = ClassChange.objects.get()
        self.assertFalse(log.ok)
        self.assertIn("대분류는 고치지 않는다", log.log)

    def test_draft_classification_line_sets_post_class(self):
        from apps.writing import drafts
        from apps.writing.models import Post
        text = ("사이트: memorily\n분류: IT/AI > AI 도구·활용\n\n<!-- 본문 시작 -->\n# AI 로 회의록 줄이기\n본문\n<!-- 본문 끝 -->\n"
                "태그: AI\n소개: 짧게\n")
        d = drafts.parse(text, "T20_회의록")
        self.assertEqual((d.site, d.classification), ("memorily", "IT/AI > AI 도구·활용"))
        with tempfile.TemporaryDirectory() as tmp, override_settings(WRITING_DRAFTS_DIR=Path(tmp)):
            (Path(tmp) / "T20_회의록").mkdir()
            (Path(tmp) / "T20_회의록" / "원고.md").write_text(text, encoding="utf-8")
            self.client.force_login(get_user_model().objects.create_user("tester3", password="pw-test-1234"))
            self.client.post(reverse("writing:import"), {"keys": ["T20_회의록"]})
        post = Post.objects.get(title="AI 로 회의록 줄이기")
        self.assertEqual((post.bt_category.name, post.summary), ("AI 도구·활용", "짧게"))


class DraftAutoImportTests(Login):
    """루틴이 쓴 원고(T26~)는 글 관리를 열면 임시 템플릿에 바로 들어온다. 그 전 원고와 이미 있는(휴지통 포함) 글은 건너뛴다."""

    def test_new_drafts_show_up_in_posts(self):
        with tempfile.TemporaryDirectory() as tmp, override_settings(WRITING_DRAFTS_DIR=Path(tmp)):
            for key, title in [("T25_옛원고", "옛 원고"), ("T26_새원고", "새 원고"), ("T27_지운원고", "지운 원고")]:
                (Path(tmp) / key).mkdir()
                (Path(tmp) / key / "원고.md").write_text(DRAFT.replace("네이버 첫 원고", title), encoding="utf-8")
            TistoryPost.objects.create(title="지운 원고").delete()  # 휴지통
            res = self.client.get(reverse("posts:index"), follow=True)
            self.assertContains(res, "새 원고 1편을 임시 템플릿으로 가져왔습니다.")
            self.client.get(reverse("posts:index"))  # 두 번 열어도 한 번만
        self.assertEqual(list(TistoryPost.objects.values_list("title", "stage")), [("새 원고", "temp")])

    def test_created_at_is_when_draft_was_written(self):
        import importlib
        import os

        from django.apps import apps as registry

        written = timezone.make_aware(timezone.datetime(2026, 10, 16, 20, 35))
        with tempfile.TemporaryDirectory() as tmp, override_settings(WRITING_DRAFTS_DIR=Path(tmp)):
            for key, title in [("T26_새원고", "새 원고"), ("T27_먼저가져온원고", "먼저 가져온 원고")]:
                (Path(tmp) / key).mkdir()
                f = Path(tmp) / key / "원고.md"
                f.write_text(DRAFT.replace("네이버 첫 원고", title), encoding="utf-8")
                os.utime(f, (written.timestamp(), written.timestamp()))  # git 밖이면 파일 시각
            early = TistoryPost.objects.create(title="먼저 가져온 원고")  # 고치기 전에 가져온 것 = 가져온 시각
            self.client.get(reverse("posts:index"))
            importlib.import_module("apps.writing.migrations.0006_draft_written_at").forward(registry, None)
        self.assertEqual(TistoryPost.objects.get(title="새 원고").created_at, written)
        early.refresh_from_db()
        self.assertEqual(early.created_at, written)
