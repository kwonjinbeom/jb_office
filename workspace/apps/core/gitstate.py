"""git 상태 조회와 동기화 실행을 Django 쪽에서 쓰기 좋게 감싼 모듈.

실제 git 명령은 tools/gitsync.py 가 담당한다. 여기서는
- 저장소 루트 탐지
- 마지막 동기화 결과를 .sync_state.json 에 저장/로드
만 추가한다. 상태 파일은 .gitignore 에 있어서 동기화 루프를 만들지 않는다.
"""
from __future__ import annotations

import json
import threading
from pathlib import Path

from django.conf import settings

import gitsync  # tools/gitsync.py (settings 에서 sys.path 에 추가됨)

_state_lock = threading.Lock()
HISTORY_LIMIT = 20


def repo_root() -> Path:
    try:
        return gitsync.repo_root(settings.BASE_DIR)
    except RuntimeError:
        return settings.REPO_ROOT


def _state_file() -> Path:
    return Path(settings.AUTOSYNC["STATE_FILE"])


def load_state() -> dict:
    path = _state_file()
    if not path.exists():
        return {"last": None, "history": []}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"last": None, "history": []}


def _save_state(state: dict) -> None:
    path = _state_file()
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def get_status(fetch: bool = False) -> dict:
    return gitsync.status(repo_root(), fetch=fetch)


def _python_executable() -> str:
    """manage.py 를 돌릴 Python 경로.

    uWSGI(PythonAnywhere) 안에서는 sys.executable 이 uwsgi 바이너리라서 쓸 수 없다.
    가상환경 prefix 아래의 python 을 우선 찾고, 없으면 sys.executable 로 돌아간다.
    """
    import sys

    candidates = [
        Path(sys.prefix) / "bin" / "python",
        Path(sys.prefix) / "Scripts" / "python.exe",
        Path(settings.BASE_DIR) / ".venv" / "bin" / "python",
        Path(settings.BASE_DIR) / ".venv" / "Scripts" / "python.exe",
    ]
    for c in candidates:
        if c.exists():
            return str(c)
    return sys.executable


def pull_and_reload() -> dict:
    """서버 역할: 코드 갱신 한 번에 끝내기.

    git pull --ff-only  →  manage.py migrate  →  manage.py collectstatic  →  reload 파일 touch
    migrate/collectstatic 은 새 코드를 읽도록 별도 프로세스(sys.executable)로 실행한다.
    """
    import os
    import subprocess
    import time

    root = repo_root()
    manage_py = Path(settings.BASE_DIR) / "manage.py"
    python = _python_executable()
    result: dict = {
        "ok": False,
        "pulled": False,
        "migrated": False,
        "collected": False,
        "reloaded": False,
        "steps": [],
        "output": "",
    }

    def run(name: str, cmd: list[str], cwd: Path, timeout: int = 180) -> bool:
        try:
            proc = subprocess.run(cmd, cwd=str(cwd), capture_output=True, timeout=timeout)
            out = ((proc.stdout or b"") + (proc.stderr or b"")).decode("utf-8", errors="replace").strip()
            ok = proc.returncode == 0
        except (OSError, subprocess.TimeoutExpired) as exc:
            out, ok = str(exc), False
        result["steps"].append({"name": name, "ok": ok, "output": out[-1500:]})
        result["output"] = out[-2000:]
        return ok

    if not run("pull", ["git", "-c", "core.quotepath=false", "pull", "--ff-only", "origin"], root, 120):
        result["error"] = "git pull 실패 (fast-forward 불가?)"
        return result
    result["pulled"] = True

    def reload_app() -> None:
        touch = settings.DEPLOY.get("RELOAD_TOUCH_FILE") or ""
        if not touch:
            return
        try:
            os.utime(touch, (time.time(), time.time()))
            result["reloaded"] = True
        except OSError as exc:
            result.setdefault("error", f"재시작 파일 touch 실패: {exc}")

    if not run("migrate", [python, str(manage_py), "migrate", "--noinput"], Path(settings.BASE_DIR)):
        result["error"] = f"migrate 실패 (python={python})"
        reload_app()  # 새 코드는 받았으니 재시작은 해 둔다
        return result
    result["migrated"] = True

    if not run("collectstatic", [python, str(manage_py), "collectstatic", "--noinput", "-v", "0"], Path(settings.BASE_DIR)):
        result["error"] = "collectstatic 실패"
        reload_app()
        return result
    result["collected"] = True

    reload_app()
    result["ok"] = "error" not in result
    return result


def run_sync(reason: str, message: str | None = None) -> dict:
    """동기화를 실행하고 결과를 상태 파일에 기록한다."""
    result = gitsync.sync(repo_root(), message)
    result["reason"] = reason
    with _state_lock:
        state = load_state()
        state["last"] = result
        history = state.get("history", [])
        history.insert(
            0,
            {
                "reason": reason,
                "ok": result["ok"],
                "committed": result["committed"],
                "pushed": result["pushed"],
                "message": result.get("message", ""),
                "error": result.get("error", ""),
                "finished_at": result.get("finished_at", ""),
            },
        )
        state["history"] = history[:HISTORY_LIMIT]
        _save_state(state)
    return result
