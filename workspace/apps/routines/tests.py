import json
import tempfile
from datetime import date
from io import StringIO
from pathlib import Path
from unittest.mock import patch
from urllib.parse import unquote_plus

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.core.models import TrashEntry
from apps.naver_writing.models import Post as NaverPost
from apps.writing.models import Post as TistoryPost

from .models import Evaluation, PromptVersion, Routine, RoutineDay, RoutinePick, RoutineRun
from .local_run import find_claude, parse_link, pull_latest, start
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
        pull = patch("apps.routines.local_run.pull_latest", return_value=(False, ""))  # 링크 테스트가 진짜 git pull 을 하지 않게
        pull.start()
        self.addCleanup(pull.stop)

    def row(self, key, **params):
        return next(r for r in self.client.get(INDEX, params).context["routines"] if r.key == key)

    def test_seed_and_screen(self):
        self.assertEqual(list(Routine.objects.values_list("key", flat=True)), ["daily_ideas", "writing", "prompt_update"])
        res = self.client.get(INDEX)
        for text in ["일일루틴", "글쓰기", "프롬프트 최신화", ">실행<", "미완료",
                     "실행 이력", ">추가 실행<"]:
            self.assertContains(res, text)
        self.assertNotContains(res, "클라우드")  # 로컬·클라우드 구분 없음
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

    def test_launcher_one_prompt_report_only_for_run_button(self):
        (self.root / "ideas" / "2026-10-14.json").write_text(json.dumps({
            "date": "2026-10-14", "title": "t", "items": [dict(
                id="a1", title="지난 후보", category="tool", audience="a", problem="p", min_product="m", money_flow="f",
                channel="c", evidence="e", risk="r", first_test="t", decision="d", sources=[])]}), encoding="utf-8")
        NaverPost.objects.create(title="이미 쓴 네이버 글")
        day = date(2026, 10, 16)
        naver = Routine.objects.get(key="writing")
        run, scheduled = launcher(naver, day, report=True), launcher(naver, day)
        for text in (run, scheduled):
            self.assertIn("`일일루틴/프롬프트/writing.md`", text)  # 같은 프롬프트 md
            self.assertIn("### 오늘 쓸 분류", text)
            self.assertIn("체크: 쇼핑커넥트 링크는", text)
            self.assertIn("이미 쓴 네이버 글", text)
            # 처음 쓸 때부터 사이트별 템플릿·카테고리 컨셉에 맞춘다 (2026-10-20 사용자)
            self.assertRegex(text, r"\n  - 말투: .*개발자")
            self.assertRegex(text, r"\n  - 카테고리: .*Java")
            self.assertNotIn("클라우드", text)  # 로컬·클라우드 구분 없음
        self.assertIn("routine_report writing <상태>", run)
        self.assertNotIn("routine_report", scheduled)
        # 글쓰기는 분류 전체 트리 대신 그날 분류(+ 고른 중분류의 소분류)만
        self.assertNotIn("### 글 분류 전체", run)
        self.assertIn("  - 소분류: ", run)
        self.assertIn("### 글 분류 전체", launcher(Routine.objects.get(key="prompt_update"), day))
        # 이미 있는 글은 최근 40줄만
        for i in range(60):
            NaverPost.objects.create(title=f"쌓인 글 {i:02d}")
        existing = launcher(naver, day).split("### 이미 있는 글")[1].split("###")[0]
        self.assertEqual(existing.count("\n- "), 40)
        self.assertIn("쌓인 글 59", existing)
        self.assertNotIn("쌓인 글 10", existing)
        ideas = launcher(Routine.objects.get(key="daily_ideas"), day)
        self.assertIn("2026-10-14 · 지난 후보", ideas)
        self.assertIn("검색 표준", ideas)

    @patch("apps.routines.local_run.WINDOWS", True)
    @patch("apps.routines.local_run.find_claude", return_value="claude")
    @patch("apps.routines.local_run.subprocess.Popen")
    def test_link_opens_terminal_with_clipboard_prompt(self, popen, _claude):
        link = "jbroutine:run?key=writing&day=2026-10-16&name=%EA%B8%80%EC%93%B0%EA%B8%B0"
        with patch("apps.routines.local_run.read_clipboard", return_value="# 일일루틴 · 글쓰기\r\n할 일"):
            call_command("routine_open", link, stdout=StringIO())
        f = self.root / "workspace" / ".routine" / "writing-2026-10-16.md"
        conf = json.loads((self.root / "workspace" / ".routine" / "settings.json").read_text(encoding="utf-8"))
        self.assertIn("Bash(git push *)", conf["permissions"]["allow"])
        self.assertEqual((conf["model"], conf["env"]["CLAUDE_CODE_SUBAGENT_MODEL"]), ("sonnet", "sonnet"))  # 루틴은 Sonnet
        self.assertIn("AskUserQuestion", conf["permissions"]["deny"])  # 방법·선택은 묻지 않는다
        self.assertIn("mcp__playwright", conf["permissions"]["allow"])  # 브라우저를 열어 직접 본다
        mcp = json.loads((self.root / "workspace" / ".routine" / "mcp.json").read_text(encoding="utf-8"))
        self.assertIn("@playwright/mcp@", " ".join(mcp["mcpServers"]["playwright"]["args"]))
        self.assertEqual(f.read_text(encoding="utf-8"), "# 일일루틴 · 글쓰기\n할 일")
        script = decoded(popen.call_args[0][0])
        self.assertIn("& 'claude' 'workspace/.routine/writing-2026-10-16.md 파일을 읽고 그대로 진행해.' '--model' 'sonnet' '--settings'", script)
        self.assertIn("mcp.json' '--append-system-prompt' '모든 말과", script)
        self.assertNotIn("cmd", popen.call_args[0][0][:1])  # cmd /k 를 거치지 않는다 (띄어쓰기 경로에서 깨졌다)
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

    @patch("apps.routines.local_run.WINDOWS", True)
    @patch("apps.routines.local_run.find_claude", return_value="claude")
    @patch("apps.routines.local_run.subprocess.Popen")
    def test_convert_link_opens_terminal_without_routine_run(self, popen, _claude):
        """사이트별 템플릿의 '변환': jbroutine:convert. 루틴 현황은 남기지 않고, 안내문은 '# 사이트 변환' 이어야 한다."""
        link = "jbroutine:convert?key=cv-101530&day=2026-10-17&name=x"
        with self.assertRaises(ValueError):
            start(link, "# 일일루틴 · 글쓰기")
        self.assertIn("사이트 변환을 시작", start(link, "# 사이트 변환 · 2026-10-17 · 1편\r\n본문"))
        folder = self.root / "workspace" / ".routine"
        self.assertEqual((folder / "cv-101530-2026-10-17.md").read_text(encoding="utf-8"), "# 사이트 변환 · 2026-10-17 · 1편\n본문")
        self.assertTrue((folder / "convert").is_dir())
        self.assertIn("'workspace/.routine/cv-101530-2026-10-17.md 파일을 읽고 그대로 진행해.'", decoded(popen.call_args[0][0]))
        self.assertFalse(RoutineRun.objects.exists())

    @patch("apps.routines.management.commands.routine_open.subprocess.call", return_value=0)
    def test_link_pulls_latest_code_first(self, call):
        """링크를 열면 먼저 git pull --ff-only. 바뀌었으면 새 코드로 다시 부르고, 실패하면 'PC 코드가 최신이 아닙니다'."""
        link = "jbroutine:convert?key=cv-203437&day=2026-10-21&name=x"
        with patch("apps.routines.local_run.pull_latest", return_value=(True, "")), \
                patch("apps.routines.local_run.start") as start_, self.assertRaises(SystemExit) as done:
            call_command("routine_open", link, "--pause", stdout=StringIO())
        self.assertEqual(done.exception.code, 0)
        self.assertEqual(call.call_args[0][0][-4:], ["routine_open", link, "--no-pull", "--pause"])
        start_.assert_not_called()  # 옛 코드로는 시작하지 않는다
        err = StringIO()
        with patch("apps.routines.local_run.pull_latest", return_value=(False, "fatal: Not possible to fast-forward")), \
                patch("apps.routines.local_run.start", return_value="시작") as start_, patch("apps.routines.local_run.read_clipboard"):
            call_command("routine_open", link, stdout=StringIO(), stderr=err)
        self.assertIn("PC 코드가 최신이 아닙니다 (git pull 실패: fatal: Not possible to fast-forward)", err.getvalue())
        start_.assert_called_once()  # 알리고 지금 코드로 계속
        with patch("apps.routines.local_run.pull_latest") as pull, patch("apps.routines.local_run.start", return_value="시작"), \
                patch("apps.routines.local_run.read_clipboard"):
            call_command("routine_open", link, "--no-pull", stdout=StringIO())
        pull.assert_not_called()

    def test_pull_latest_reports_change_or_error(self):
        from subprocess import CompletedProcess

        def git(heads, pull_code=0, pull_err=""):
            out = iter(heads)
            return lambda args, **kw: (CompletedProcess(args, pull_code, "", pull_err) if args[1] == "pull"
                                       else CompletedProcess(args, 0, next(out) + "\n", ""))
        with patch("apps.routines.local_run.subprocess.run", side_effect=git(["a1", "b2"])) as run:
            self.assertEqual(pull_latest(), (True, ""))
        self.assertIn(["git", "pull", "--ff-only", "-q"], [c.args[0] for c in run.call_args_list])
        self.assertEqual(run.call_args.kwargs["env"]["GIT_TERMINAL_PROMPT"], "0")
        with patch("apps.routines.local_run.subprocess.run", side_effect=git(["a1", "a1"])):
            self.assertEqual(pull_latest(), (False, ""))
        with patch("apps.routines.local_run.subprocess.run", side_effect=git(["a1"], 128, "error: 로컬 변경\nfatal: 중단\n")):
            self.assertEqual(pull_latest(), (False, "error: 로컬 변경 / fatal: 중단"))
        with patch("apps.routines.local_run.subprocess.run", side_effect=FileNotFoundError("git 없음")):
            self.assertEqual(pull_latest(), (False, "git 없음"))

    def test_terminal_command_keeps_spaced_paths_and_quotes(self):
        """C:\\Program Files 처럼 띄어쓰기·괄호 든 claude 경로와 ' 가 든 인자도 PowerShell 문자열로 그대로 넘긴다."""
        from .local_run import terminal_command
        cmd = terminal_command("일일루틴 글쓰기", r"C:\Program Files (x86)\nodejs\claude.cmd", ["읽고 진행해.", "it's 50% & <끝>"])
        self.assertEqual(cmd[:2], ["powershell.exe", "-NoLogo"])
        self.assertIn("-NoExit", cmd)
        script = decoded(cmd)
        self.assertIn("& 'C:\\Program Files (x86)\\nodejs\\claude.cmd' '읽고 진행해.' 'it''s 50% & <끝>'", script)
        self.assertIn("$Host.UI.RawUI.WindowTitle = '일일루틴 글쓰기'", script)

    def test_find_claude_falls_back_to_desktop_app(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict("os.environ", {"USERPROFILE": tmp + "/home"}):
            for ver in ["2.1.9", "2.1.295", "2.1.271"]:
                d = Path(tmp) / "Claude" / "claude-code" / ver / "abc"
                d.mkdir(parents=True)
                (d / "claude.exe").write_text("")
            with patch("apps.routines.local_run.shutil.which", return_value=None), patch.dict("os.environ", {"APPDATA": tmp, "LOCALAPPDATA": tmp}):
                self.assertIn("2.1.295", find_claude())  # PATH 에 없으면 데스크톱 앱의 최신 버전
            store = Path(tmp) / "Packages" / "Claude_pzs8" / "LocalCache" / "Roaming" / "Claude" / "claude-code" / "2.1.300" / "abc"
            store.mkdir(parents=True)
            (store / "claude.exe").write_text("")
            with patch("apps.routines.local_run.shutil.which", return_value=None), patch.dict("os.environ", {"APPDATA": tmp + "/none", "LOCALAPPDATA": tmp}):
                self.assertIn("2.1.300", find_claude())  # 스토어 앱은 실제 파일이 Packages 아래에 있다
            data = Path(tmp) / "Claude-Data" / "claude_pzs8" / "claude-code" / "2.1.304" / "aed6"
            data.mkdir(parents=True)
            (data / "claude.exe").write_text("")
            with patch("apps.routines.local_run.shutil.which", return_value=None), patch.dict("os.environ", {"APPDATA": tmp + "/none", "LOCALAPPDATA": tmp}):
                self.assertIn("2.1.304", find_claude())  # 2026-10-21 데스크톱 앱의 새 위치 (Claude-Data)
            cli = Path(tmp) / "home" / ".local" / "bin"
            cli.mkdir(parents=True)
            (cli / "claude.exe").write_text("")
            with patch("apps.routines.local_run.shutil.which", return_value=None), patch.dict("os.environ", {"APPDATA": tmp, "LOCALAPPDATA": tmp}):
                self.assertEqual(find_claude(), str(cli / "claude.exe"))  # 공식 CLI 설치 위치가 먼저
            (cli / "claude.exe").unlink()
            with patch("apps.routines.local_run.shutil.which", return_value=None), patch.dict("os.environ", {"APPDATA": tmp + "/none", "LOCALAPPDATA": tmp + "/none"}):
                with self.assertRaises(RuntimeError):
                    find_claude()
        with patch("apps.routines.local_run.shutil.which", return_value="/usr/bin/claude"):
            self.assertEqual(find_claude(), "/usr/bin/claude")

    def test_run_button_copies_and_opens_link(self):
        with override_settings(IS_SERVER=True):
            res = self.client.get(INDEX)
        self.assertContains(res, '<form class="rt-launch"><input type="hidden" name="key" value="writing">')
        self.assertNotContains(res, "/routines/launch/")  # PC 서버로 보내지 않는다
        self.assertContains(res, "실행 이력")  # 모든 루틴의 실행 기록 (예약 · 실행)

    def test_naver_import_drafts(self):
        folder = self.root.joinpath("콘텐츠", "블로그_카페", "포스팅자동화", "네이버원고", "N01_첫원고")
        folder.mkdir(parents=True)
        (folder / "원고.md").write_text(DRAFT, encoding="utf-8")
        self.assertContains(self.client.get(reverse("naver_writing:import")), "네이버 첫 원고")
        self.client.post(reverse("naver_writing:import"), {"keys": ["N01_첫원고"]})
        post = NaverPost.objects.get(title="네이버 첫 원고")
        self.assertEqual((post.stage, post.tags, post.summary), ("temp", "하나, 둘", "짧은 소개"))


class RepoTests(Login):
    """저장소의 실제 md (일일루틴/프롬프트) 를 쓴다."""

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

    def test_references_are_md_reads_and_data(self):
        tistory = Routine.objects.get(key="writing")
        refs = references(tistory)
        self.assertEqual([r["kind"] for r in refs][:1], ["프롬프트"])
        labels = [r["label"] for r in refs]
        for label in ["일일루틴/프롬프트/writing.md", "AGENTS.md", "일일루틴/프롬프트/writing_checklist.md", "일일루틴/프롬프트/writing_sources.md",
                      "일일루틴/분류변경/README.md",
                      "오늘 쓸 분류", "사이트·체크 (운영 화면)"]:
            self.assertIn(label, labels)
        self.assertNotIn("workspace/TISTORY_WRITER.md", labels)  # 보조는 짧은 체크리스트만 읽는다 (2026-10-19)
        self.assertEqual(labels.count("일일루틴/프롬프트/writing_checklist.md"), 1)  # 짧게 다시 적은 경로는 같은 파일
        self.assertTrue(all(r["ok"] for r in refs))
        self.assertFalse(any("T번호" in label for label in labels))  # 쓰는 곳은 '보는 md'가 아니다

    def test_prompts_page_tabs_refs_and_versions(self):
        res = self.client.get(PROMPTS, {"r": "writing"})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context["routine"].key, "writing")
        for text in ["글쓰기", "프롬프트 최신화", "writing_checklist.md", "나의 평가", "프롬프트 이력", "v1",
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
        text = launcher(refresh, date(2026, 10, 16), report=True)
        self.assertIn("`일일루틴/프롬프트/prompt_update.md`", text)
        self.assertIn("### 글쓰기 — `일일루틴/프롬프트/writing.md`", text)
        self.assertIn("2026-10-15 · 3점 [새] · 제목이 길다", text)
        self.assertIn("점검 관점: AI 글쓰기 유의점", text)
        self.assertIn("routine_report prompt_update", text)
        self.assertIn("### 글 분류 전체 (대 > 중 > 소)", text)  # 분류마다 깊은 조사 (0009)
        res = self.client.get(PROMPTS, {"r": "writing"})
        self.assertEqual(res.context["new_count"], 1)
        # 프롬프트 md 가 바뀌어 새 버전이 생기면 그 전 평가는 '반영'
        v1 = PromptVersion.objects.get(routine=tistory)
        PromptVersion.objects.create(routine=tistory, number=2, sha="x", content="바뀐 프롬프트")
        self.assertEqual(self.client.get(PROMPTS, {"r": "writing"}).context["new_count"], 0)
        self.assertIn("3점 · 제목이 길다", launcher(Routine.objects.get(key="prompt_update"), date(2026, 10, 16)))
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

    @patch("apps.routines.local_run.find_claude", return_value="claude")
    @patch("apps.routines.local_run.subprocess.Popen")
    def test_all_run_order_update_writing_ideas(self, popen, _claude):
        res = self.client.get(INDEX, {"date": "2026-10-16"})
        self.assertContains(res, ">전체 실행<")
        text = res.context["all_prompt"]
        self.assertIn("순서: 1. 프롬프트 최신화 → 2. 글쓰기 → 3. 일일 아이디어", text)
        self.assertLess(text.index("# 일일루틴 · 프롬프트 최신화"), text.index("# 일일루틴 · 글쓰기"))
        self.assertLess(text.index("# 일일루틴 · 글쓰기"), text.index("# 일일루틴 · 일일 아이디어"))
        self.assertEqual(text.count("## 진행 보고"), 3)
        self.assertEqual(res.context["all_keys"], "prompt_update,writing,daily_ideas")
        with tempfile.TemporaryDirectory() as tmp, override_settings(BASE_DIR=Path(tmp)), patch("apps.routines.local_run.WINDOWS", True):
            folder = Path(tmp) / ".routine"
            (folder / "done").mkdir(parents=True)
            (folder / "done" / "all-2026-10-16-2-writing.md").write_text("완료", encoding="utf-8")  # 앞서 누른 것
            msg = start(f"jbroutine:all?key=all&day=2026-10-16&keys={res.context['all_keys']}", text.replace("\n", "\r\n"))
            self.assertIn("루틴마다 새 터미널로 차례로", msg)
            # 루틴마다 따로 된 안내문 (한 대화로 잇지 않는다) + 끝 표시 파일 지시
            names = ["all-2026-10-16-1-prompt_update.md", "all-2026-10-16-2-writing.md", "all-2026-10-16-3-daily_ideas.md"]
            bodies = [(folder / n).read_text(encoding="utf-8") for n in names]
            self.assertTrue(bodies[1].startswith("# 일일루틴 · 글쓰기"))
            self.assertNotIn("# 일일루틴 · 프롬프트 최신화", bodies[1])
            self.assertEqual(bodies[1].count("## 진행 보고"), 1)
            self.assertIn("`workspace/.routine/done/all-2026-10-16-2-writing.md` 파일을 만든다", bodies[1])
            self.assertFalse((folder / "done" / names[1]).exists())  # 다시 누르면 처음부터
            # 차례 창: 루틴 터미널을 하나씩 열고, 끝 표시나 창 닫힘을 기다린 뒤 다음
            raw = (folder / "all-chain.ps1").read_bytes()
            self.assertTrue(raw.startswith(b"\xef\xbb\xbf"))
            chain = raw.decode("utf-8-sig")
            self.assertEqual(chain.count("Start-Process"), 3)
            self.assertLess(chain.index("1/3 프롬프트 최신화"), chain.index("2/3 글쓰기"))
            self.assertIn(f"Test-Path -LiteralPath '{folder / 'done' / names[0]}'", chain)
            self.assertIn("$p.HasExited", chain)
            self.assertIn("-File", popen.call_args[0][0])
            self.assertIn("taskkill /PID $script:prev.Id /T /F", chain)  # 끝난 루틴 창은 닫는다 (2026-10-20 사용자)
            self.assertEqual(chain.count("Close-Done 90"), 4)  # 루틴마다 + 마지막
            self.assertNotIn("-NoExit", popen.call_args[0][0])  # 다 끝나면 차례 창도 닫힌다
        windows = [c for c in popen.call_args_list if c[0][0][0] == "powershell.exe"]
        self.assertEqual(len(windows), 1)  # 창은 차례 창 하나만 바로 연다 (나머지는 원고 가져오기의 git)
        self.assertEqual(RoutineRun.objects.count(), 3)
        with self.assertRaises(ValueError):
            start("jbroutine:all?key=all&day=2026-10-16", "# 일일루틴 전체 실행 — 2026-10-16\n루틴 없음")

    def test_report_api_records_run_history(self):
        from apps.core.models import ROUTINE_BRIEF_TOKEN_KEY, AppSetting
        url = reverse("routines:report", args=["writing"])
        self.assertEqual(self.client.post(url + "?token=x", {"status": "시작"}).status_code, 403)
        AppSetting.set(ROUTINE_BRIEF_TOKEN_KEY, "tok")
        self.client.logout()
        q = "?token=tok&day=2026-10-17&via=schedule"
        self.assertEqual(self.client.post(url + q, {"status": "아무말"}).status_code, 400)
        self.assertEqual(self.client.post(url + q, {"status": "시작", "step": "오늘 11편"}).status_code, 200)
        # Windows curl 은 한글을 cp949 로 보낸다 (2026-10-20 보고가 모두 400 이었다)
        cp949 = "status=%BF%CF%B7%E1&step=%BF%F8%B0%ED+11%C6%ED%2C+main+push"  # 완료 / 원고 11편, main push
        self.assertEqual(unquote_plus(cp949, encoding="cp949"), "status=완료&step=원고 11편, main push")
        res = self.client.post(url + q, cp949, content_type="application/x-www-form-urlencoded")
        self.assertEqual(res.status_code, 200)
        run = RoutineRun.objects.get()
        self.assertEqual((run.via, run.status, run.day, run.log.count("\n")), ("schedule", "done", date(2026, 10, 17), 1))
        self.client.force_login(get_user_model().objects.get(username="tester"))
        res = self.client.get(INDEX, {"date": "2026-10-17"})
        self.assertContains(res, "실행 이력")
        self.assertContains(res, "원고 11편, main push")
        self.assertContains(res, ">예약<")
        # 토큰이 있으면 화면의 '실행' 안내문도 서버로 보고한다 (via=run)
        row = next(r for r in res.context["routines"] if r.key == "writing")
        self.assertIn("/routines/report/writing/?token=tok&day=2026-10-17&via=run", row.prompt)

    def test_extra_writing_by_categories_or_comment(self):
        from apps.blog_types.models import Category
        writing = Routine.objects.get(key="writing")
        url = reverse("routines:extra", args=[writing.pk])
        it = Category.objects.get(section__name="IT/AI", name="AI 도구·활용")
        res = self.client.post(url, {"day": "2026-10-16", "mode": "cats", f"n_{it.sel}": "2"})
        text = res.json()["prompt"]
        self.assertTrue(text.startswith("# 일일루틴 · 글쓰기 (추가 실행) — 2026-10-16"))
        self.assertIn("### 이번에 할 것 (추가 실행)\n(총 2편 · 추가로 고른 분류)\n- IT/AI > AI 도구·활용 — 2편", text)
        self.assertNotIn("### 오늘 쓸 분류", text)
        self.assertIn("### 이미 있는 글", text)  # 겹침 피하기 자료는 그대로
        self.assertFalse(RoutinePick.objects.exists())  # 추가 실행은 그날 아침 분량을 저장하지 않는다
        res = self.client.post(url, {"day": "2026-10-16", "mode": "comment", "comment": "IT/AI 로 3편, 아이폰 18 가격 비교"})
        self.assertIn("사용자 코멘트: IT/AI 로 3편, 아이폰 18 가격 비교", res.json()["prompt"])
        self.assertIn("### 글 분류 전체", res.json()["prompt"])  # 코멘트로 시키면 분류를 골라야 해서 트리를 싣는다
        self.assertNotIn("### 글 분류 전체", text)
        self.assertEqual(self.client.post(url, {"mode": "comment", "comment": " "}).status_code, 400)
        self.assertEqual(self.client.post(url, {"mode": "cats"}).status_code, 400)
        page = self.client.get(reverse("routines:extra_page"), {"r": "writing", "date": "2026-10-16"})
        for html in ['data-ex-mode="cats" class="on"', 'data-ex-mode="comment"', ">추가 실행<", 'id="ex-comment"',
                     "10월 16일 하루 분량", 'id="pk-morning"']:
            self.assertContains(page, html)
        self.assertNotContains(page, 'class="num-in pk-n" type="number" min="0" max="20" name="n_c' + str(it.pk) + '" value')  # 빈 칸으로 시작

    def test_extra_daily_ideas_by_count(self):
        ideas = Routine.objects.get(key="daily_ideas")
        url = reverse("routines:extra", args=[ideas.pk])
        text = self.client.post(url, {"day": "2026-10-16", "mode": "count", "count": "4", "comment": "겨울 시즌 상품"}).json()["prompt"]
        self.assertTrue(text.startswith("# 일일루틴 · 일일 아이디어 (추가 실행) — 2026-10-16"))
        self.assertIn("### 이번에 할 것 (추가 실행)\n4개 더 한다.\n방향 (사용자 코멘트): 겨울 시즌 상품", text)
        self.assertIn("### 검색 표준", text)
        for bad in ["0", "31", "x"]:
            self.assertEqual(self.client.post(url, {"mode": "count", "count": bad}).status_code, 400)
        page = self.client.get(reverse("routines:extra_page"), {"r": "daily_ideas"})
        self.assertContains(page, 'name="count"')
        self.assertContains(page, 'data-mode="count"')
        index = self.client.get(INDEX)
        self.assertContains(index, ">실행<")  # 예약이 안 돌았을 때 손으로
        self.assertContains(index, f'{reverse("routines:extra_page")}?r=daily_ideas')

    def test_capture_version_when_md_changes(self):
        tistory = Routine.objects.get(key="writing")
        v1 = capture_version(tistory)
        with patch("apps.routines.views._read", return_value="새 내용"):
            v2 = capture_version(tistory)
        self.assertEqual((v1.number, v2.number, v2.content), (1, 2, "새 내용"))

    def test_doc_only_for_referenced_md(self):
        self.assertContains(self.client.get(reverse("routines:doc", args=["일일루틴/프롬프트/writing_checklist.md"])), "원고 체크리스트")
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
    """글쓰기: 그날 쓸 분류 (기본 광고 6 · 판매 3 · IT/AI 2), 고르기·다시 뽑기·기본값 (추가 실행 화면)."""

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
        text = launcher(self.writing, date(2026, 10, 16))
        self.assertIn("(총 4편 · 사용자가 고른 분류)", text)
        self.assertIn("- IT/AI > AI 도구·활용 — 3편", text)
        res = self.client.get(INDEX, {"date": "2026-10-16"})
        row = next(r for r in res.context["routines"] if r.key == "writing")
        self.assertEqual(row.target, 4)
        page = self.client.get(reverse("routines:extra_page"), {"r": "writing", "date": "2026-10-16"})
        self.assertTrue(page.context["picker"]["custom"])
        self.assertContains(page, "IT/AI &gt; AI 도구·활용 <strong>3편</strong>")
        res = self.client.post(self.url, {"day": "2026-10-16", "action": "reroll"})
        self.assertEqual(res.url, reverse("routines:extra_page") + "?r=writing&date=2026-10-16#ex-morning")
        self.assertEqual(sum(RoutinePick.objects.get().picks.values()), 11)
        self.client.post(self.url, {"day": "2026-10-16", "action": "default"})
        self.assertFalse(RoutinePick.objects.exists())


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
    """루틴이 쓴 원고(T26~)는 글 관리를 열면 임시글에 바로 들어온다. 그 전 원고와 이미 있는(휴지통 포함) 글은 건너뛴다."""

    def test_new_drafts_show_up_in_posts(self):
        with tempfile.TemporaryDirectory() as tmp, override_settings(WRITING_DRAFTS_DIR=Path(tmp)):
            for key, title in [("T25_옛원고", "옛 원고"), ("T26_새원고", "새 원고"), ("T27_지운원고", "지운 원고")]:
                (Path(tmp) / key).mkdir()
                (Path(tmp) / key / "원고.md").write_text(DRAFT.replace("네이버 첫 원고", title), encoding="utf-8")
            TistoryPost.objects.create(title="지운 원고").delete()  # 휴지통
            res = self.client.get(reverse("posts:index"), follow=True)
            self.assertContains(res, "새 원고 1편을 임시글으로 가져왔습니다.")
            self.client.get(reverse("posts:index"))  # 두 번 열어도 한 번만
        self.assertEqual(list(TistoryPost.objects.values_list("title", "stage")), [("새 원고", "temp")])

    def test_routines_screen_imports_new_drafts_for_count(self):
        """글 관리를 안 열어도 일일루틴 화면이 새 원고를 가져와 글쓰기 결과에 센다 (2026-10-20)."""
        with tempfile.TemporaryDirectory() as tmp, override_settings(WRITING_DRAFTS_DIR=Path(tmp)):
            (Path(tmp) / "T61_새원고").mkdir()
            (Path(tmp) / "T61_새원고" / "원고.md").write_text(DRAFT.replace("네이버 첫 원고", "오늘 쓴 원고"), encoding="utf-8")
            row = next(r for r in self.client.get(INDEX).context["routines"] if r.key == "writing")
        self.assertTrue(TistoryPost.objects.filter(title="오늘 쓴 원고").exists())
        self.assertEqual(row.result, 1)

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


def decoded(cmd):
    """terminal_command 가 -EncodedCommand 로 넘긴 PowerShell 스크립트."""
    import base64
    return base64.b64decode(cmd[cmd.index("-EncodedCommand") + 1]).decode("utf-16-le")


class FixedTopicTests(Login):
    """커스텀 글쓰기 (2026-10-21 사용자): 고정 주제를 주 단위로 쓰고 발행 여부를 점으로 본다. 일일루틴 글쓰기 줄 아래로 펼친다."""

    def test_seed_page_and_weekly_dots(self):
        from datetime import timedelta

        from django.utils import timezone

        from .models import FixedTopic, TopicWeek, week_start
        names = list(FixedTopic.objects.values_list("name", flat=True))
        self.assertEqual(names[:2], ["공모주 일정 · 국내", "공모주 일정 · 해외"])  # 나머지는 지역별 (test_topic_feedback_migration)
        res = self.client.get(reverse("routines:topics"))
        self.assertEqual(res.context["ACTIVE_MENU"], "routine_topics")
        self.assertEqual(len(res.context["weeks"]), 8)
        t = FixedTopic.objects.get(name="공모주 일정 · 국내")
        today = timezone.localdate()
        url = reverse("routines:topic_week", args=[t.pk])
        self.client.post(url, {"week": today.isoformat(), "next": "/routines/topics/"})
        self.assertTrue(TopicWeek.objects.get(topic=t, week=week_start(today)).published)
        res = self.client.get(reverse("routines:topics"))
        self.assertEqual(res.context["done_this_week"], 1)
        self.client.post(url, {"week": (week_start(today) + timedelta(days=3)).isoformat()})  # 그 주 어느 날이든 같은 주
        self.assertFalse(TopicWeek.objects.get(topic=t, week=week_start(today)).published)

    def test_add_edit_and_prompt(self):
        from .models import FixedTopic
        self.client.post(reverse("routines:topic_add"), {"name": "  청약   일정 · 수도권 "})
        t = FixedTopic.objects.get(name="청약 일정 · 수도권")
        self.client.post(reverse("routines:topic_save", args=[t.pk]),
                         {"name": "청약 일정 · 수도권", "site": "눈잎", "per_week": "2", "note": "이번 주 청약 단지와 당첨 발표일만"})
        t.refresh_from_db()
        self.assertEqual((t.site, t.per_week, t.note), ("눈잎", 2, "이번 주 청약 단지와 당첨 발표일만"))
        res = self.client.get(reverse("routines:topics"))
        prompt = next(x for x in res.context["topics"] if x.pk == t.pk).prompt
        self.assertTrue(prompt.startswith("# 일일루틴 · 글쓰기 (추가 실행)"))  # 글쓰기 루틴의 추가 실행처럼 PC 터미널에서
        for text in ["고정 주제 (커스텀 글쓰기): 청약 일정 · 수도권 — 2편", "사이트: 눈잎", "이번 주 청약 단지와 당첨 발표일만",
                     "고정주제: 청약 일정 · 수도권"]:
            self.assertIn(text, prompt)
        self.client.post(reverse("routines:topic_delete", args=[t.pk]))
        self.assertFalse(FixedTopic.objects.filter(pk=t.pk).exists())
        self.assertTrue(FixedTopic.all_objects.filter(pk=t.pk).exists())  # 휴지통

    def test_index_writing_row_unfolds_topics(self):
        res = self.client.get(reverse("routines:index"))
        self.assertContains(res, 'class="rt-has-sub" data-rt-toggle')
        self.assertContains(res, "공모주 일정 · 해외")
        self.assertContains(res, "data-rt-sub hidden", count=5)  # 주제 넷 + 추가 줄
        self.assertEqual(len(res.context["fixed_topics"][0].cells), 4)  # 최근 4주

    def test_free_writing_box_and_compact_picker(self):
        writing = Routine.objects.get(key="writing")
        res = self.client.get(reverse("routines:topics"))
        self.assertContains(res, 'id="tp-free-text"')  # 왼쪽 자유 글쓰기
        self.assertContains(res, f'data-url="{reverse("routines:extra", args=[writing.pk])}"')
        data = self.client.post(reverse("routines:extra", args=[writing.pk]),
                                {"mode": "comment", "comment": "신혼부부 전세대출 금리 비교 2편", "day": "2026-10-21"}).json()
        self.assertIn("신혼부부 전세대출 금리 비교 2편", data["prompt"])
        res = self.client.get(reverse("routines:extra_page"), {"r": "writing"})
        self.assertContains(res, "data-pk-tog")  # 하위 타입은 접어 둔다
        self.assertContains(res, '<div class="pk-types" hidden>', html=False)

    def test_topic_feedback_migration(self):
        """주제별 피드백 (2026-10-21 사용자): 정책·청약 공고는 따로, 서울·경기는 한 글 안에서 나눈다, 공모주는 앞으로 한 달·분기"""
        from .models import FixedTopic
        names = list(FixedTopic.objects.values_list("name", flat=True))
        self.assertEqual(names, ["공모주 일정 · 국내", "공모주 일정 · 해외", "청년·신혼 정책 (서울·경기)", "청약·임대주택 공고 (서울·경기)"])
        self.assertEqual(FixedTopic.all_objects.filter(deleted_at__isnull=False).count(), 2)  # 경기 주제 둘은 휴지통
        kr = FixedTopic.objects.get(name="공모주 일정 · 국내")
        self.assertIn("앞으로 한 달", kr.note)
        self.assertIn("최대한 많이", kr.note)
        housing = FixedTopic.objects.get(name="청약·임대주택 공고 (서울·경기)")
        self.assertIn("한 글 안에서 '서울' · '경기' 소제목으로 나눠 쓴다", housing.note)
        self.assertIn("SH 서울주택도시공사 · GH 경기주택도시공사", housing.note)
        policy = FixedTopic.objects.get(name="청년·신혼 정책 (서울·경기)")
        self.assertIn("주택 청약·임대 공고는 다루지 않는다", policy.note)
        self.assertNotIn("기존 지침", policy.note)
        prompt = self.client.get(reverse("routines:topics")).context["topics"][0].prompt
        self.assertIn("공모주는 앞으로 한 달·분기", prompt)
        self.assertIn("최대한 많이", prompt)

    def test_run_all_topics(self):
        """전체 실행 (2026-10-21 사용자): 고정 주제 모두를 한 터미널에서 차례로"""
        res = self.client.get(reverse("routines:topics"))
        text = res.context["all_prompt"]
        self.assertTrue(text.startswith("# 일일루틴 · 글쓰기 (추가 실행)"))
        self.assertIn("고정 주제 전체 실행 (커스텀 글쓰기): 아래 4개 주제를 순서대로", text)
        for n, name in enumerate(["공모주 일정 · 국내", "공모주 일정 · 해외", "청년·신혼 정책 (서울·경기)", "청약·임대주택 공고 (서울·경기)"], 1):
            self.assertIn(f"#### {n}. {name}", text)
        self.assertContains(res, "전체 실행")
        res = self.client.get(reverse("routines:index"))
        self.assertContains(res, "고정 주제 전체 실행")
