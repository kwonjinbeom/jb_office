"""로컬 실행: 일일루틴 화면의 '실행' → `jbroutine:` 링크 → PC 의 `manage.py routine_open` 이 claude 터미널을 연다.

PC 서버(run.bat)가 꺼져 있어도 된다 (2026-10-16 사용자: "누르면 알아서 클로드 켜서 묻지 말고 프롬프트대로").
화면은 안내문을 클립보드에 복사한 뒤 링크를 연다. 링크는 run.bat / routine_link.bat 이 Windows 에 한 번 등록한다.
claude 는 단계마다 `manage.py routine_report` 로 PC DB 에 현황(RoutineRun)을 남긴다.

링크: jbroutine:<run|update|all|convert|feeds>?key=<루틴 키>&day=YYYY-MM-DD&name=<이름>[&keys=a,b,c]
convert: 글 관리의 '변환'·'전체 변환'·'재변환'. 안내문은 '# 사이트 변환' 으로 시작하고 (site_templates/prompt.launcher),
루틴 현황은 남기지 않는다. key 는 그때마다 다른 이름(cv-시분초)이라 여러 번 눌러도 안내문 파일이 겹치지 않는다.
anime: 애니 총정리의 '글쓰기·변환' (2026-10-23 사용자). 일일루틴과 따로, 작품마다 새 터미널을 차례로 (전체 실행과 같은 차례 창).
안내문은 '# 애니 총정리' 로 시작하고 (apps/anime/run.py), 루틴 현황은 남기지 않는다.
클립보드에 없으면 링크의 key 로 서버(settings.SERVER_URL)에서 받는다 (2026-10-27, anime_brief).
feeds: 모니터링의 '발행 확인' (2026-10-22 사용자). claude 없이 PC 가 사이트마다 RSS 를 읽어 서버로 보낸다 (check_feeds).
서버(PythonAnywhere 무료)는 티스토리·네이버에 못 나가서다. '전체 실행' 안내문에도 같은 것이 숨어 있어(FEEDS_MARK) 매일 같이 한다.
"""
import base64
import json
import urllib.request
import os
import re
import shutil
import subprocess
import time
from datetime import date
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit

from django.conf import settings
from django.utils import timezone

from .models import Routine, RoutineRun

WINDOWS = os.name == "nt"
SCHEME = "jbroutine"
KINDS = ("run", "update", "all", "convert", "feeds", "anime")
KEY = re.compile(r"[a-z0-9_-]{1,30}")
PROMPT_HEAD = "# 일일루틴"  # launcher · all_prompt · restore_prompt 가 모두 이렇게 시작한다
CONVERT_HEAD = "# 사이트 변환"  # apps/site_templates/prompt.LAUNCH_HEAD
ANIME_HEAD = "# 애니 총정리"  # apps/anime/run.HEAD
ANIME_PART = re.compile(r"^<!-- 애니 총정리 작품: (a[0-9]{1,8}) -->\n", re.M)  # apps/anime/run.PART
FEEDS_HEAD = "# 발행 확인"  # apps/blog_ops/views.CHECK_HEAD
FEEDS_MARK = re.compile(r"^<!-- 발행 확인 (\{.*\}) -->$", re.M)  # 전체 실행 안내문에 숨긴 발행 확인 (routines.views.index)

# 로컬 실행 claude 에 미리 허용하는 것: 루틴이 늘 하는 일 (저장소 안 읽기·쓰기, 웹 검색, 브라우저, git 올리기, 진행 보고).
# 묻는 건 권한이 없어 막힐 때만 (2026-10-16 사용자). 방법·선택을 묻는 질문 도구와 크롬 확장(사이트마다 허락을 묻는다)은 막는다.
# 브라우저: Playwright MCP 가 PC 의 크롬을 새 창(루틴 전용 프로필)으로 열어 claude 가 직접 검색·클릭·읽기를 한다.
# 네이버·티스토리처럼 WebFetch 로는 안 읽히는 곳을 사람이 보듯 본다 (2026-10-16 사용자: "예전엔 브라우저를 열어 조작해서 확인했다").
PLAYWRIGHT_MCP = "@playwright/mcp@0.0.83"
MCP_SERVERS = {"playwright": {"command": "cmd", "args": ["/c", "npx", "-y", PLAYWRIGHT_MCP]}}
ROUTINE_ALLOW = [
    "Read", "Edit", "Write", "Glob", "Grep", "WebSearch", "WebFetch", "mcp__playwright",
    "Bash(git add *)", "Bash(git commit *)", "Bash(git push *)", "Bash(git pull *)", "Bash(git fetch *)",
    "Bash(git status *)", "Bash(git log *)", "Bash(git diff *)", "Bash(ls *)", "Bash(mkdir *)",
    "Bash(curl *)",  # 진행 보고를 서버 실행 이력으로 (views.report_api)
    "Bash(workspace/.venv/Scripts/python workspace/manage.py routine_report *)",
    "Bash(workspace/.venv/Scripts/python.exe workspace/manage.py routine_report *)",
    # 사이트 변환 뒤 워드프레스 초안 올리기 (2026-10-26, site_templates.wp_rest)
    "Bash(workspace/.venv/Scripts/python workspace/manage.py wp_draft *)",
    "Bash(workspace/.venv/Scripts/python.exe workspace/manage.py wp_draft *)",
]
ROUTINE_DENY = ["AskUserQuestion", "mcp__claude-in-chrome"]
# 애니 글쓰기·변환은 회차 데이터·환산기 빌드·가공이미지를 파이썬으로 돌린다 (애니환산기/build.py · 그림.py, 자동완성 조사)
ANIME_ALLOW = ["Bash(python *)", "Bash(py *)", "Bash(workspace/.venv/Scripts/python.exe *)"]
# 루틴은 Sonnet 으로 (2026-10-19 사용자: Opus 는 한 번에 5시간 한도를 많이 쓴다). 보조 claude(서브에이전트)도 같은 모델.
ROUTINE_MODEL = "sonnet"
KOREAN = ("모든 말과 진행 보고는 한국어로 한다. 루틴은 스스로 판단해 끝까지 진행하고, 방법·선택·확인을 사용자에게 묻지 않는다. "
          "사용자에게 묻는 건 권한이 없어 실행이 막힐 때뿐이고, 그때는 무엇을 왜 하려는지 한국어로 한 줄 먼저 말한다. "
          "블로그·검색·트렌드 사이트는 브라우저(playwright 도구: browser_navigate·browser_snapshot·browser_click)로 직접 열어 보고, "
          "브라우저가 안 뜨면 WebFetch·WebSearch 로 한다. 둘 다 안 되는 페이지는 막힘으로 보고하고 넘어간다. 로그인·글쓰기·게시는 하지 않는다. "
          "셸 명령은 Bash 도구로 저장소 폴더에서 실행한다.")


def parse_link(link):
    """jbroutine: 링크 → {kind, key, day, name, keys}. 올바르지 않으면 ValueError."""
    parts = urlsplit(link.strip())
    kind = unquote(parts.path or parts.netloc).strip("/")
    q = {k: v[0] for k, v in parse_qs(parts.query).items()}
    key = q.get("key", "")
    if parts.scheme != SCHEME or kind not in KINDS or not KEY.fullmatch(key):
        raise ValueError(f"실행 링크가 올바르지 않습니다: {link}")
    try:
        day = date.fromisoformat(q.get("day", ""))
    except ValueError:
        day = timezone.localdate()
    keys = [k for k in q.get("keys", "").split(",") if KEY.fullmatch(k)]
    return {"kind": kind, "key": key, "day": day, "name": q.get("name", "")[:40], "keys": keys}


def read_clipboard():
    """Windows 클립보드의 글 (화면이 '실행'을 누를 때 안내문을 복사해 둔다)."""
    if not WINDOWS:
        raise RuntimeError("클립보드 읽기는 Windows PC 에서만 됩니다.")
    import ctypes
    from ctypes import wintypes

    user32, kernel32 = ctypes.WinDLL("user32"), ctypes.WinDLL("kernel32")
    user32.OpenClipboard.argtypes = [wintypes.HWND]
    user32.GetClipboardData.argtypes = [wintypes.UINT]
    user32.GetClipboardData.restype = wintypes.HANDLE
    kernel32.GlobalLock.argtypes = [wintypes.HGLOBAL]
    kernel32.GlobalLock.restype = ctypes.c_void_p
    kernel32.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
    for _ in range(20):  # 브라우저가 막 복사한 참이면 잠깐 잡혀 있을 수 있다
        if user32.OpenClipboard(None):
            break
        time.sleep(0.1)
    else:
        raise RuntimeError("클립보드를 열지 못했습니다.")
    try:
        handle = user32.GetClipboardData(13)  # CF_UNICODETEXT
        if not handle:
            return ""
        ptr = kernel32.GlobalLock(handle)
        try:
            return ctypes.wstring_at(ptr) if ptr else ""
        finally:
            kernel32.GlobalUnlock(handle)
    finally:
        user32.CloseClipboard()


def _routine_for(key, name=""):
    return Routine.objects.filter(key=key).first() or Routine.objects.create(
        key=key, name=(name or key)[:40], url_name="routines:index", task="(실서버에서 보낸 루틴)")


def _open_run(routine, day, step):
    run = RoutineRun.objects.filter(routine=routine, day=day).first()
    if run is None or not run.is_open:
        run = RoutineRun.objects.create(routine=routine, day=day)
    run.report(RoutineRun.Status.RUNNING, step, timezone.localtime())


def find_claude():
    """claude 실행 파일. PATH 에 없으면 데스크톱 앱에 든 것 중 최신 버전 (claude-code/<버전>/<해시>/claude.exe).
    2026-10-17: 이 PC 는 데스크톱 앱만 있어 PATH 의 'claude' 를 못 찾고 터미널이 바로 닫혔다.
    스토어(MSIX) 앱은 %APPDATA% 가 가상화되어 실제 파일이 %LOCALAPPDATA%/Packages/Claude_*/LocalCache/Roaming 에 있다.
    2026-10-21: 데스크톱 앱이 %LOCALAPPDATA%/Claude-Data/claude_*/claude-code 로 옮겨 다시 못 찾았다.
    공식 CLI 설치 위치(~/.local/bin/claude.exe)는 PATH 에 없어도 먼저 본다."""
    found = shutil.which("claude")
    if found:
        return found
    cli = Path(os.environ.get("USERPROFILE") or Path.home()) / ".local" / "bin" / "claude.exe"
    if cli.is_file():
        return str(cli)
    roaming, local = Path(os.environ.get("APPDATA", "")), Path(os.environ.get("LOCALAPPDATA", ""))
    bases = [roaming / "Claude" / "claude-code"]
    if (local / "Claude-Data").is_dir():
        bases += [p / "claude-code" for p in (local / "Claude-Data").glob("claude_*")]
    if (local / "Packages").is_dir():
        bases += [p / "LocalCache" / "Roaming" / "Claude" / "claude-code" for p in (local / "Packages").glob("Claude_*")]

    def version(p):
        return tuple(int(n) if n.isdigit() else 0 for n in p.parent.parent.name.split("."))

    exes = sorted((exe for base in bases if base.is_dir() for exe in base.glob("*/*/claude.exe")), key=version)
    if not exes:
        raise RuntimeError("claude 를 찾지 못했습니다. Claude 데스크톱 앱이나 Claude Code CLI 를 설치하세요.")
    return str(exes[-1])


def _ps(value):
    """PowerShell 작은따옴표 문자열 (안의 ' 는 '' 로)."""
    return "'" + str(value).replace("'", "''") + "'"


def terminal_command(title, claude, args):
    """새 콘솔 창에서 claude 를 여는 명령 (PowerShell, 스크립트는 -EncodedCommand 로 넘긴다).

    2026-10-19: 예전에는 cmd /c start … cmd /k "C:/Program Files/…/claude.cmd" "…" 로 열었는데, cmd /k 는 줄이 따옴표로
    시작하고 따옴표가 여럿이면 맨 앞·맨 뒤 따옴표를 떼어 버려 "'C:/Program'은(는) … 명령이 아닙니다" 로 터미널이 바로 실패했다
    (claude 가 띄어쓰기 든 경로에 깔린 PC 마다). cmd 를 거치지 않으면 띄어쓰기·괄호·한글 경로와 인자가 그대로 간다.
    """
    script = "; ".join([
        f"$Host.UI.RawUI.WindowTitle = {_ps(title)}",
        f"Set-Location -LiteralPath {_ps(settings.REPO_ROOT)}",
        "& " + _ps(claude) + " " + " ".join(_ps(a) for a in args),
    ])
    encoded = base64.b64encode(script.encode("utf-16-le")).decode("ascii")
    return ["powershell.exe", "-NoLogo", "-NoProfile", "-NoExit", "-ExecutionPolicy", "Bypass", "-EncodedCommand", encoded]


def _claude_args(name, allow=()):
    """claude 에 넘길 인자 (미리 허용한 것 + 브라우저 + 한국어). 설정 파일을 .routine 에 쓴다.
    allow: 이 실행만 더 허용할 것 (애니 글쓰기·변환의 파이썬). 다른 루틴과 섞이지 않게 설정 파일을 따로 쓴다."""
    folder = settings.BASE_DIR / ".routine"
    folder.mkdir(exist_ok=True)
    conf, mcp = folder / ("settings-extra.json" if allow else "settings.json"), folder / "mcp.json"
    conf.write_text(json.dumps({"model": ROUTINE_MODEL, "env": {"CLAUDE_CODE_SUBAGENT_MODEL": ROUTINE_MODEL},
                                "permissions": {"allow": ROUTINE_ALLOW + list(allow), "deny": ROUTINE_DENY}},
                               ensure_ascii=False, indent=2), encoding="utf-8")
    mcp.write_text(json.dumps({"mcpServers": MCP_SERVERS}, indent=2), encoding="utf-8")
    ask = f"workspace/.routine/{name} 파일을 읽고 그대로 진행해."
    return [ask, "--model", ROUTINE_MODEL, "--settings", str(conf), "--mcp-config", str(mcp), "--append-system-prompt", KOREAN]


def _manual(name):
    return (f'claude "workspace/.routine/{name} 파일을 읽고 그대로 진행해." --model {ROUTINE_MODEL} '
            "--settings workspace/.routine/settings.json --mcp-config workspace/.routine/mcp.json")


def pull_latest():
    """링크를 열 때마다 PC 저장소를 main 최신으로 (git pull --ff-only). (바뀌었나, 실패 이유) 를 돌려준다.
    2026-10-21: PC 폴더가 main 보다 100 커밋 늦어 '사이트 변환' 링크(convert)를 몰라 "실행 링크가 올바르지 않습니다" 로 막혔다."""
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}  # 로그인을 물으며 멈추지 않게

    def git(*args):
        return subprocess.run(["git", *args], cwd=str(settings.REPO_ROOT), env=env, capture_output=True,
                              text=True, encoding="utf-8", errors="replace", timeout=60)

    try:
        before = git("rev-parse", "HEAD").stdout.strip()
        res = git("pull", "--ff-only", "-q")
        if res.returncode:
            why = " / ".join(line.strip() for line in (res.stderr or res.stdout).splitlines() if line.strip())
            return False, (why or f"git 종료 코드 {res.returncode}")[:300]
        return git("rev-parse", "HEAD").stdout.strip() != before, ""
    except (OSError, subprocess.TimeoutExpired) as e:
        return False, str(e)[:300]


def _popen(command):
    subprocess.Popen(command, cwd=str(settings.REPO_ROOT), creationflags=getattr(subprocess, "CREATE_NEW_CONSOLE", 0))


def open_terminal(name, title, claude="claude"):
    """새 터미널에서 claude 를 연다. Windows 가 아니면 돌릴 명령을 돌려준다."""
    args = _claude_args(name)
    if not WINDOWS:
        return _manual(name)
    _popen(terminal_command(title, claude, args))
    return ""


# 전체 실행: 루틴마다 새 터미널 (2026-10-19 사용자: 한 대화로 이으면 답할 때마다 앞 루틴 대화까지 다시 읽어 토큰이 크게 는다).
# 작은 창(차례 창)이 루틴 터미널을 하나씩 열고, claude 가 끝 표시 파일(.routine/done/)을 남기거나 창이 닫히면 다음 루틴을 연다.
# 끝 표시 첫 줄이 '실패'면 그 루틴 창은 닫지 않는다 (2026-10-28 사용자: 지역 놀거리를 시각 확인 못 해 못 썼는데 창이 닫혀
# 이유를 못 봤다 — 실패면 터미널을 열어 두고 마지막에 사유를 보여 줘, 이어서 부탁해 보게). 소재 없음·예정은 실패가 아니다.
# views.ALL_PART · 여러 날 글쓰기는 키 뒤에 날짜 (views.DAY_PART, 2026-10-31) — 그 루틴의 현황·안내문을 그 날짜로
# · 변환까지 (views.CONVERT_PART, 2026-10-31): '변환: 날짜 주소' — 앞 글쓰기가 끝나면 그 주소에서 변환 안내문을 받아 연다
ALL_PART = re.compile(r"^<!-- 일일루틴 (?:루틴: ([a-z0-9_-]{1,30})(?: (\d{4}-\d{2}-\d{2}))?"
                      r"|변환: (\d{4}-\d{2}-\d{2}) (https?://\S+)) -->\n?", re.M)
CLOSE_AFTER = 90  # 끝 표시 뒤 루틴 창을 닫기까지 (초)
FAILED = "실패"  # 끝 표시 첫 줄
DONE_TAIL = """
## 끝나면 (전체 실행)
완료(또는 막힘·실패) 보고를 남긴 뒤, 맨 마지막에 Write 도구로 저장소 폴더의 `workspace/.routine/done/{name}` 파일을 만든다.
- 실패가 없으면 내용은 `완료` 한 줄. 이 창은 잠시 뒤 닫힌다.
- 실패가 하나라도 있으면 첫 줄은 `실패`, 그 아래 줄마다 `- 무엇: 사유`
  (예: `- black_lukey 지역 놀거리 · 단양 당일치기: 버스·열차 시각을 공식 출처로 확인하지 못함`). 이 창은 닫히지 않는다.
- 실패 = 하려고 고른 일을 확인 못 함·막힘·오류로 끝내 못 한 것. 소재 '없음', 쓸 시각 전 '예정', 새 소식이 없어 안 쓴 것은 실패가 아니다.
이 파일이 생기면 다음 루틴이 새 터미널에서 시작된다. 그 뒤에는 도구를 쓰지 않는다.
실패가 있었으면 맨 마지막 답의 끝에 `## 실패한 것` 을 두고 줄마다 무엇 · 사유 · 이어서 부탁하면 할 수 있는 것 한 줄
(예: "코레일·버스 회사 시간표로 다시 찾아 써 줘"라고 하면 이어서 쓴다)을 적는다. 사용자가 이 창에서 보고 이어서 부탁한다.
"""


def split_parts(text, part=ALL_PART):
    """안내문 → [(경계 표시의 묶음들, 그 부분의 안내문)]."""
    marks = list(part.finditer(text))
    ends = [m.start() for m in marks[1:]] + [len(text)]
    return [(m.groups(), text[m.end():end].strip() + "\n") for m, end in zip(marks, ends)]


def split_all(text, part=ALL_PART):
    """전체 실행 안내문 → [(루틴 키, 그 루틴의 안내문)]. 애니 글쓰기·변환은 part=ANIME_PART (작품마다)."""
    return [(groups[0], body) for groups, body in split_parts(text, part)]


def open_chain(steps, title, claude="claude", allow=()):
    """steps: [(안내문 파일 이름, 창 제목[, 먼저 할 명령])]. 먼저 할 명령이 있으면 그 차례에 돌리고 (변환까지: 안내문 받기),
    0 으로 끝나야 그 터미널을 연다 — 아니면 건너뛴다. 차례 창 하나가 루틴 터미널을 앞 루틴이 끝날 때마다 하나씩 연다.
    끝난 루틴 창은 CLOSE_AFTER 초 뒤 닫고(마지막 답·Stop 훅의 git 동기화가 끝나게), 다 끝나면 차례 창도 닫힌다
    (2026-10-20 사용자: 끝났으면 창을 닫았으면). 끝 표시 없이 사람이 창을 닫은 루틴은 그대로 다음으로 간다.
    끝 표시 첫 줄이 '실패'인 루틴 창은 닫지 않고, 차례 창도 다 끝난 뒤 Enter 를 기다린다 (2026-10-28 사용자)."""
    folder = settings.BASE_DIR / ".routine"
    done = folder / "done"
    done.mkdir(parents=True, exist_ok=True)
    if not WINDOWS:
        return " → 끝나면 ".join(_manual(name) for name, _ in steps)
    lines = [
        f"$Host.UI.RawUI.WindowTitle = {_ps(title)}", f"Set-Location -LiteralPath {_ps(settings.REPO_ROOT)}",
        "$prev = $null; $prevAt = Get-Date; $kept = 0",
        "function Close-Done([int]$wait) { if ($script:prev) { $left = $wait - ((Get-Date) - $script:prevAt).TotalSeconds; "
        "if ($left -gt 0) { Start-Sleep -Seconds ([int]$left) }; "
        "if (-not $script:prev.HasExited) { taskkill /PID $script:prev.Id /T /F | Out-Null }; $script:prev = $null } }",
    ]
    for name, step_title, *before in steps:
        (done / name).unlink(missing_ok=True)  # 같은 날 다시 누르면 처음부터
        flag = _ps(done / name)
        argv = terminal_command(step_title, claude, _claude_args(name, allow))
        block = [
            f"Write-Host {_ps(f'{step_title} 시작 (새 터미널)')}",
            f"$p = Start-Process -FilePath {_ps(argv[0])} -ArgumentList {','.join(_ps(a) for a in argv[1:])} -PassThru",
            f"while (-not (Test-Path -LiteralPath {flag}) -and -not $p.HasExited) {{ Start-Sleep -Seconds 10; "
            f"if ($prev -and ((Get-Date) - $prevAt).TotalSeconds -ge {CLOSE_AFTER}) {{ Close-Done 0 }} }}",
            f"Close-Done {CLOSE_AFTER}",
            # 끝 표시 첫 줄이 '실패'면 그 창은 닫을 차례에 넣지 않고, 사유를 이 창에도 적는다
            f"$failed = (Test-Path -LiteralPath {flag}) -and "
            f"((Get-Content -LiteralPath {flag} -Encoding UTF8 -TotalCount 1) -like {_ps(FAILED + '*')})",
            f"if ($failed) {{ $kept += 1; Write-Host {_ps(f'{step_title}: 실패가 있어 그 창을 열어 둡니다.')}; "
            f"Get-Content -LiteralPath {flag} -Encoding UTF8 | Select-Object -Skip 1 | ForEach-Object {{ Write-Host ('  ' + $_) }} }}",
            f"elseif (Test-Path -LiteralPath {flag}) {{ $prev = $p; $prevAt = Get-Date }}",
            f"Write-Host {_ps(f'{step_title} 끝')}",
        ]
        if before:  # 앞 터미널이 끝난 뒤 돌리는 명령. 0 이 아니면 (변환할 글 없음 · 실패) 이 터미널은 건너뛴다
            lines += [f"Write-Host {_ps(f'{step_title} 준비')}", before[0],
                      "if ($LASTEXITCODE -eq 0) {", *block, f"}} else {{ Write-Host {_ps(f'{step_title} 건너뜀')} }}"]
        else:
            lines += block
    lines += [f"Close-Done {CLOSE_AFTER}",
              f"if ($kept) {{ Write-Host ({_ps('전체 실행을 마쳤습니다. 실패한 루틴 ')} + $kept + "
              f"{_ps('개의 창은 열어 두었습니다. 그 창에서 이어서 부탁하세요.')}); Read-Host {_ps('Enter 를 누르면 이 창을 닫습니다')} }}",
              f"else {{ Write-Host {_ps('전체 실행을 마쳤습니다. 이 창은 10초 뒤 닫힙니다.')}; Start-Sleep -Seconds 10 }}"]
    script = folder / "all-chain.ps1"
    script.write_text("\n".join(lines) + "\n", encoding="utf-8-sig")  # BOM: Windows PowerShell 5.1 이 한글을 깨뜨리지 않게
    _popen(["powershell.exe", "-NoLogo", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script)])
    return ""


def convert_command(url, name):
    """변환 단계의 '먼저 할 명령' (PowerShell 한 줄): manage.py routine_convert 가 서버에서 안내문을 받아 .routine/<name> 에 쓴다."""
    python = settings.BASE_DIR / ".venv" / "Scripts" / "python.exe"
    return (f"& {_ps(python if python.exists() else 'python')} {_ps(settings.BASE_DIR / 'manage.py')} routine_convert "
            f"{_ps(url)} {_ps(name)}")


def fetch_convert(url, name, head="", wait=20, tries=45, opener=None):
    """변환까지: 서버(views.convert_api)에서 그날 변환 안내문을 받아 .routine/<name> 에 쓴다 (+ 끝 표시 지시).
    서버에 아직 PC 커밋이 없으면(409, 웹훅 반영 전) wait 초마다 다시 묻는다. (0=씀 · 3=변환할 글 없음 · 1=실패, 한 줄)."""
    import urllib.error
    opener = opener or urllib.request.urlopen
    full = url + ("&" if "?" in url else "?") + f"head={head}" if head else url
    for i in range(tries):
        try:
            with opener(full, timeout=120) as res:
                if res.status == 204:
                    return 3, "변환할 글이 없습니다 (그날 쓴 글이 없거나 이미 변환)."
                text = res.read().decode("utf-8").replace("\r\n", "\n")
        except urllib.error.HTTPError as e:
            if e.code == 409 and i < tries - 1:
                time.sleep(wait)
                continue
            return 1, f"변환 안내문을 받지 못했습니다 (HTTP {e.code})."
        except OSError as e:
            return 1, f"변환 안내문을 받지 못했습니다 ({e})."
        if not text.startswith(CONVERT_HEAD):
            return 1, "서버 응답이 변환 안내문이 아닙니다."
        folder = settings.BASE_DIR / ".routine"
        (folder / "convert").mkdir(parents=True, exist_ok=True)
        (folder / name).write_text(text + DONE_TAIL.format(name=name), encoding="utf-8")
        return 0, f"변환 안내문을 받았습니다 ({text.splitlines()[0]})."
    return 1, "서버에 새 원고가 아직 반영되지 않았습니다 (기다리다 멈춤)."


def check_feeds(payload):
    """PC 에서 사이트마다 RSS 와 공개 통계(방문자 · 공감 · 댓글)를 읽어 서버(payload['api'])로 보낸다.
    서버가 남긴 결과를 한 줄씩 돌려준다."""
    from apps.blog_ops import feeds
    results = []
    for f in payload.get("feeds") or []:
        ok, message, items = feeds.read(f.get("url", ""), where="PC")
        results.append({"blog": f.get("blog"), "ok": ok, "message": message,
                        "items": [[t, u, w.isoformat()] for t, u, w in items]})
    from apps.blog_ops import stats
    numbers = [stats.collect(s) for s in payload.get("stats") or []]  # 통계현황: 방문자 · 공감 · 댓글
    from . import site_views
    ga4 = site_views.collect()  # 통계현황: GA4 날짜별 방문자·조회 · 많이 본 글 · 유입 (인증 없으면 빈 목록)
    body = json.dumps({"token": payload.get("token", ""), "results": results, "stats": numbers, "ga4": ga4},
                      ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(payload["api"], data=body, headers={"Content-Type": "application/json; charset=utf-8"})
    with urllib.request.urlopen(req, timeout=60) as res:
        out = json.loads(res.read().decode("utf-8"))
    return "\n".join(f"- {r['blog']}: {r['message']}" for r in out.get("results", [])) or "- (운영 중인 사이트 없음)"


def _feeds_in(text):
    m = FEEDS_MARK.search(text)
    return json.loads(m.group(1)) if m else None


def start(link, text):
    """링크와 안내문으로 실행을 시작한다: 안내문 저장 → 로컬 현황 기록 → claude 터미널. 알릴 한 줄을 돌려준다."""
    req = parse_link(link)
    text = text.replace("\r\n", "\n")
    kind, key, day = req["kind"], req["key"], req["day"]
    if kind == "feeds":
        if not text.startswith(FEEDS_HEAD):
            raise ValueError("클립보드에 발행 확인 안내가 없습니다. 모니터링에서 '발행 확인'을 다시 누르세요.")
        return "발행 확인을 마쳤습니다. 모니터링 화면이 곧 새로고침됩니다.\n" + check_feeds(json.loads(text[len(FEEDS_HEAD):].strip()))
    if kind == "anime":
        if not text.startswith(ANIME_HEAD):  # 클립보드가 비었거나 그새 다른 걸 복사했으면 서버에서 받는다
            text, why = anime_brief(key)
            if not text:
                raise ValueError(f"애니 글쓰기·변환 안내문을 받지 못했습니다 ({why}). 애니 총정리에서 '글쓰기·변환'을 다시 누르세요.")
        return _start_anime(text, day, find_claude() if WINDOWS else "claude")
    if kind == "convert":
        if not text.startswith(CONVERT_HEAD):  # 브라우저가 복사를 거절했거나 그새 다른 걸 복사했으면 서버에서 받는다 (2026-10-28)
            text, why = server_brief(f"blog/site-templates/brief/{key}/", CONVERT_HEAD)
            if not text:
                raise ValueError(f"사이트 변환 안내문을 받지 못했습니다 ({why}). 발행예정글에서 '변환'을 다시 누르세요.")
    elif not text.startswith(PROMPT_HEAD):
        raise ValueError("클립보드에 일일루틴 안내문이 없습니다. 화면에서 '실행'을 다시 누르세요.")
    claude = find_claude() if WINDOWS else "claude"  # 못 찾으면 현황을 남기기 전에 멈춘다
    if kind == "convert":
        name, title = f"{key}-{day}.md", "사이트 변환"
        done = "PC 터미널에서 사이트 변환을 시작했습니다. 끝나면 사이트별 템플릿을 새로고침하세요."
    elif kind == "all":
        parts = split_parts(text)
        if not parts:
            raise ValueError("전체 실행 안내문에 루틴이 없습니다. 화면에서 '전체 실행'을 다시 누르세요.")
        folder = settings.BASE_DIR / ".routine"
        folder.mkdir(exist_ok=True)
        steps, days = [], any(on for (_, on, _, _), _ in parts)  # 여러 날 글쓰기: 날마다 그 날짜로
        for i, ((k, on, cday, curl), body) in enumerate(parts, start=1):
            if cday:  # 변환까지: 앞 글쓰기가 끝나면 서버에서 그날 변환 안내문을 받아 이 파일에 쓴다 (routine_convert)
                name = f"all-{cday}-{i}-convert.md"
                (folder / name).unlink(missing_ok=True)
                steps.append((name, f"일일루틴 {i}/{len(parts)} 변환 {cday[5:]}", convert_command(curl, name)))
                continue
            routine, when = _routine_for(k), date.fromisoformat(on) if on else day
            _open_run(routine, when, ("여러 날 글쓰기" if days else "전체 실행") + " · 차례를 기다립니다")
            name = f"all-{when}-{i}-{k}.md"
            (folder / name).write_text(body + DONE_TAIL.format(name=name), encoding="utf-8")
            steps.append((name, f"일일루틴 {i}/{len(parts)} {routine.name}" + (f" {when:%m-%d}" if on else "")))
        what = "여러 날 글쓰기" if days else "전체 실행"
        manual = open_chain(steps, f"일일루틴 {what} (차례 창)", claude)
        said = (f"저장소 폴더에서 차례로 실행하세요: {manual}" if manual else
                f"PC 에서 {what}을 시작했습니다 ({f'{len(parts)}일, 날마다' if days else f'{len(parts)}개 루틴, 루틴마다'} 새 터미널로 차례로).")
        payload = _feeds_in(text)
        if payload:  # 루틴 창이 열린 뒤 발행 확인도 (실패해도 전체 실행은 그대로)
            try:
                said += "\n발행 확인:\n" + check_feeds(payload)
            except Exception as e:  # noqa: BLE001 — 네트워크·서버 오류는 알리기만
                said += f"\n발행 확인을 하지 못했습니다: {e}"
        return said
    else:
        routine = _routine_for(key, req["name"])
        label = "갱신" if kind == "update" else "루틴"
        _open_run(routine, day, f"{label} · 터미널을 열었습니다 (claude 시작 대기)")
        name, title = f"{key}-{'update-' if kind == 'update' else ''}{day}.md", f"일일루틴 {routine.name} {label}"
        done = f"PC 터미널에서 {routine.name} {label}을 시작했습니다."
    folder = settings.BASE_DIR / ".routine"
    (folder / "convert").mkdir(parents=True, exist_ok=True)  # 변환본 본문 파일 자리 (prompt.launcher)
    (folder / name).write_text(text, encoding="utf-8")
    manual = open_terminal(name, title, claude)
    return f"저장소 폴더에서 실행하세요: {manual}" if manual else done


def anime_brief(key):
    """서버에 잠깐 둔 애니 글쓰기·변환 안내문 (apps/anime/views.brief). (안내문, 못 받은 이유)."""
    return server_brief(f"anime/brief/{key}/", ANIME_HEAD)


def server_brief(path, head):
    """서버에 잠깐 둔 안내문 (apps/core/briefs). (안내문, 못 받은 이유)."""
    url = f"{settings.SERVER_URL.rstrip('/')}/{path}"
    try:
        with urllib.request.urlopen(url, timeout=30) as res:
            text = res.read().decode("utf-8").replace("\r\n", "\n")
    except Exception as e:  # noqa: BLE001 — 404(30분 지남·다시 누름)·네트워크 오류는 이유만 알린다
        return "", f"클립보드에 없고 서버에서도 못 받음: {e}"
    return (text, "") if text.startswith(head) else ("", "클립보드에 없고 서버 응답도 안내문이 아님")


def _start_anime(text, day, claude):
    """애니 글쓰기·변환: 작품마다 안내문 파일 → 차례 창이 작품마다 새 터미널을 연다 (끝 표시는 전체 실행과 같다)."""
    parts = split_all(text, ANIME_PART)
    if not parts:
        raise ValueError("안내문에 작품이 없습니다. 애니 총정리에서 '글쓰기·변환'을 다시 누르세요.")
    folder = settings.BASE_DIR / ".routine"
    folder.mkdir(exist_ok=True)
    steps = []
    for i, (k, body) in enumerate(parts, start=1):
        name = f"anime-{day}-{i}-{k}.md"
        (folder / name).write_text(body + DONE_TAIL.format(name=name), encoding="utf-8")
        title = re.search(r"^## (.+?) —", body, re.M)
        steps.append((name, f"애니 글쓰기·변환 {i}/{len(parts)} {title.group(1) if title else k}"))
    manual = open_chain(steps, "애니 글쓰기·변환 (차례 창)", claude, ANIME_ALLOW)
    return (f"저장소 폴더에서 차례로 실행하세요: {manual}" if manual else
            f"PC 에서 애니 글쓰기·변환을 시작했습니다 ({len(parts)}작품, 작품마다 새 터미널로 차례로).")
