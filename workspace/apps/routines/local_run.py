"""로컬 실행: 일일루틴 화면의 '실행' → `jbroutine:` 링크 → PC 의 `manage.py routine_open` 이 claude 터미널을 연다.

PC 서버(run.bat)가 꺼져 있어도 된다 (2026-10-16 사용자: "누르면 알아서 클로드 켜서 묻지 말고 프롬프트대로").
화면은 안내문을 클립보드에 복사한 뒤 링크를 연다. 링크는 run.bat / routine_link.bat 이 Windows 에 한 번 등록한다.
claude 는 단계마다 `manage.py routine_report` 로 PC DB 에 현황(RoutineRun)을 남긴다.

링크: jbroutine:<run|update|all>?key=<루틴 키>&day=YYYY-MM-DD&name=<이름>[&keys=a,b,c]
"""
import json
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
KINDS = ("run", "update", "all")
KEY = re.compile(r"[a-z0-9_-]{1,30}")
PROMPT_HEAD = "# 일일루틴"  # launcher · all_prompt · restore_prompt 가 모두 이렇게 시작한다

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
    "Bash(workspace/.venv/Scripts/python workspace/manage.py routine_report *)",
    "Bash(workspace/.venv/Scripts/python.exe workspace/manage.py routine_report *)",
]
ROUTINE_DENY = ["AskUserQuestion", "mcp__claude-in-chrome"]
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
    """claude 실행 파일. PATH 에 없으면 데스크톱 앱에 든 것 중 최신 버전 (%APPDATA%/Claude/claude-code/<버전>/<해시>/claude.exe).
    2026-10-17: 이 PC 는 데스크톱 앱만 있어 PATH 의 'claude' 를 못 찾고 터미널이 바로 닫혔다."""
    found = shutil.which("claude")
    if found:
        return found
    base = Path(os.environ.get("APPDATA", "")) / "Claude" / "claude-code"

    def version(p):
        return tuple(int(n) if n.isdigit() else 0 for n in p.parent.parent.name.split("."))

    exes = sorted(base.glob("*/*/claude.exe"), key=version) if base.is_dir() else []
    if not exes:
        raise RuntimeError("claude 를 찾지 못했습니다. Claude 데스크톱 앱이나 Claude Code CLI 를 설치하세요.")
    return str(exes[-1])


def open_terminal(name, title, claude="claude"):
    """새 터미널에서 claude 를 연다 (미리 허용한 것 + 브라우저 + 한국어). Windows 가 아니면 돌릴 명령을 돌려준다."""
    folder = settings.BASE_DIR / ".routine"
    folder.mkdir(exist_ok=True)
    conf, mcp = folder / "settings.json", folder / "mcp.json"
    conf.write_text(json.dumps({"permissions": {"allow": ROUTINE_ALLOW, "deny": ROUTINE_DENY}}, ensure_ascii=False, indent=2), encoding="utf-8")
    mcp.write_text(json.dumps({"mcpServers": MCP_SERVERS}, indent=2), encoding="utf-8")
    ask = f"workspace/.routine/{name} 파일을 읽고 그대로 진행해."
    if not WINDOWS:
        return f'claude "{ask}" --settings workspace/.routine/settings.json --mcp-config workspace/.routine/mcp.json'
    subprocess.Popen(["cmd", "/c", "start", title, "/D", str(settings.REPO_ROOT), "cmd", "/k", claude, ask,
                      "--settings", str(conf), "--mcp-config", str(mcp), "--append-system-prompt", KOREAN])
    return ""


def start(link, text):
    """링크와 안내문으로 실행을 시작한다: 안내문 저장 → 로컬 현황 기록 → claude 터미널. 알릴 한 줄을 돌려준다."""
    req = parse_link(link)
    text = text.replace("\r\n", "\n")
    if not text.startswith(PROMPT_HEAD):
        raise ValueError("클립보드에 일일루틴 안내문이 없습니다. 화면에서 '실행'을 다시 누르세요.")
    claude = find_claude() if WINDOWS else "claude"  # 못 찾으면 현황을 남기기 전에 멈춘다
    kind, key, day = req["kind"], req["key"], req["day"]
    if kind == "all":
        for k in req["keys"]:
            _open_run(_routine_for(k), day, "전체 실행 · 차례를 기다립니다")
        name, title = f"all-{day}.md", "일일루틴 전체 실행"
        done = f"PC 터미널에서 전체 실행을 시작했습니다 ({len(req['keys'])}개 루틴, 차례로)."
    else:
        routine = _routine_for(key, req["name"])
        label = "갱신" if kind == "update" else "루틴"
        _open_run(routine, day, f"{label} · 터미널을 열었습니다 (claude 시작 대기)")
        name, title = f"{key}-{'update-' if kind == 'update' else ''}{day}.md", f"일일루틴 {routine.name} {label}"
        done = f"PC 터미널에서 {routine.name} {label}을 시작했습니다."
    folder = settings.BASE_DIR / ".routine"
    folder.mkdir(exist_ok=True)
    (folder / name).write_text(text, encoding="utf-8")
    manual = open_terminal(name, title, claude)
    return f"저장소 폴더에서 실행하세요: {manual}" if manual else done
