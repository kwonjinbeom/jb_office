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


def pull_and_reload() -> dict:
    """서버 역할: git pull --ff-only 로 코드를 받고, 설정된 파일을 touch 해 앱을 재시작시킨다."""
    import os
    import subprocess
    import time

    root = repo_root()
    result: dict = {"ok": False, "pulled": False, "reloaded": False, "output": ""}
    try:
        proc = subprocess.run(
            ["git", "-c", "core.quotepath=false", "pull", "--ff-only", "origin"],
            cwd=str(root),
            capture_output=True,
            timeout=120,
        )
        out = ((proc.stdout or b"") + (proc.stderr or b"")).decode("utf-8", errors="replace").strip()
        result["output"] = out[-2000:]
        if proc.returncode != 0:
            result["error"] = "git pull 실패 (fast-forward 불가?)"
            return result
        result["pulled"] = True
    except (OSError, subprocess.TimeoutExpired) as exc:
        result["error"] = str(exc)
        return result

    touch = settings.DEPLOY.get("RELOAD_TOUCH_FILE") or ""
    if touch:
        try:
            os.utime(touch, (time.time(), time.time()))
            result["reloaded"] = True
        except OSError as exc:
            result["error"] = f"재시작 파일 touch 실패: {exc}"
            return result
    result["ok"] = True
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
