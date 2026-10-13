"""Git auto-sync helper. Standard library only.

Used by three callers:
  1. Claude Code Stop hook (after every turn)
  2. Django background thread (apps/core/autosync.py)
  3. Manual run: python tools/gitsync.py

Flow: add -A -> commit (if changes) -> pull --rebase --autostash -> push.
Every step is recorded so the home screen can display the result.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import subprocess
import sys
import time
from pathlib import Path

LOCK_NAME = ".gitsync.lock"
LOCK_STALE_SECONDS = 600


def _run(args: list[str], cwd: Path, timeout: int = 120) -> tuple[int, str]:
    env = dict(os.environ)
    env.setdefault("GIT_TERMINAL_PROMPT", "0")
    try:
        proc = subprocess.run(
            ["git", "-c", "core.quotepath=false", *args],
            cwd=str(cwd),
            capture_output=True,
            timeout=timeout,
            env=env,
        )
    except FileNotFoundError:
        return 127, "git executable not found"
    except subprocess.TimeoutExpired:
        return 124, f"git {' '.join(args)} timed out after {timeout}s"
    out = (proc.stdout or b"") + (proc.stderr or b"")
    return proc.returncode, out.decode("utf-8", errors="replace").strip()


def repo_root(start: Path | None = None) -> Path:
    start = start or Path(__file__).resolve().parent
    code, out = _run(["rev-parse", "--show-toplevel"], start)
    if code != 0:
        raise RuntimeError(f"not a git repository: {start}")
    return Path(out)


def status(root: Path, fetch: bool = False) -> dict:
    """Snapshot of the repository for display. Never raises."""
    info: dict = {"ok": True, "root": str(root)}
    if fetch:
        code, out = _run(["fetch", "--quiet", "origin"], root, timeout=60)
        info["fetch_ok"] = code == 0
        if code != 0:
            info["fetch_error"] = out

    code, out = _run(["branch", "--show-current"], root)
    info["branch"] = out if code == 0 else "?"

    code, out = _run(["remote", "get-url", "origin"], root)
    info["remote"] = out if code == 0 else ""

    code, out = _run(["status", "--porcelain=v1", "--untracked-files=all"], root)
    changes = []
    if code == 0 and out:
        for line in out.splitlines():
            if len(line) < 4:
                continue
            xy, path = line[:2], line[3:]
            if " -> " in path:
                path = path.split(" -> ", 1)[1]
            changes.append({"status": xy.strip() or "??", "path": path.strip('"')})
    info["changes"] = changes
    info["dirty"] = len(changes)

    code, out = _run(["rev-list", "--left-right", "--count", "HEAD...@{upstream}"], root)
    if code == 0 and out:
        parts = out.split()
        info["ahead"] = int(parts[0])
        info["behind"] = int(parts[1]) if len(parts) > 1 else 0
    else:
        info["ahead"] = None
        info["behind"] = None

    code, out = _run(
        ["log", "-8", "--date=iso-strict", "--pretty=format:%h%x1f%ad%x1f%an%x1f%s"], root
    )
    commits = []
    if code == 0 and out:
        for line in out.splitlines():
            parts = line.split("\x1f")
            if len(parts) == 4:
                commits.append(
                    {"hash": parts[0], "date": parts[1], "author": parts[2], "subject": parts[3]}
                )
    info["commits"] = commits
    info["checked_at"] = _dt.datetime.now().isoformat(timespec="seconds")
    return info


class _Lock:
    def __init__(self, root: Path):
        self.path = root / LOCK_NAME
        self.fd: int | None = None

    def __enter__(self):
        try:
            if self.path.exists():
                age = time.time() - self.path.stat().st_mtime
                if age > LOCK_STALE_SECONDS:
                    self.path.unlink(missing_ok=True)
            self.fd = os.open(str(self.path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(self.fd, str(os.getpid()).encode())
        except FileExistsError:
            raise RuntimeError("another sync is already running")
        return self

    def __exit__(self, *exc):
        if self.fd is not None:
            os.close(self.fd)
        self.path.unlink(missing_ok=True)


def sync(root: Path, message: str | None = None) -> dict:
    """Commit everything and push. Returns a result dict; never raises."""
    started = _dt.datetime.now()
    result: dict = {
        "ok": False,
        "started_at": started.isoformat(timespec="seconds"),
        "steps": [],
        "committed": False,
        "pushed": False,
    }

    def step(name: str, code: int, out: str) -> bool:
        ok = code == 0
        result["steps"].append({"name": name, "ok": ok, "output": out[-2000:]})
        return ok

    try:
        with _Lock(root):
            code, out = _run(["branch", "--show-current"], root)
            branch = out if code == 0 else ""
            result["branch"] = branch
            if not branch:
                result["error"] = "detached HEAD; nothing synced"
                return result

            code, out = _run(["add", "-A"], root)
            if not step("add", code, out):
                result["error"] = "git add failed"
                return result

            code, _ = _run(["diff", "--cached", "--quiet"], root)
            if code == 1:
                msg = message or f"sync: {started.strftime('%Y-%m-%d_%H-%M-%S')}"
                code, out = _run(["commit", "-q", "-m", msg], root)
                if not step("commit", code, out):
                    result["error"] = "git commit failed"
                    return result
                result["committed"] = True
                result["message"] = msg
            else:
                step("commit", 0, "no local changes")

            # 1차: fast-forward 만 시도. 2차: 갈라졌으면 merge 로 합친다.
            # (rebase 는 로컬에 merge 커밋이 있을 때 그 안의 커밋을 다시 재생하려다 충돌을 낸다)
            code, out = _run(["pull", "--ff-only", "--quiet", "origin", branch], root)
            if code != 0:
                code, out = _run(
                    ["pull", "--no-rebase", "--no-edit", "--autostash", "--quiet", "origin", branch], root
                )
                if code != 0:
                    _run(["merge", "--abort"], root)
            if not step("pull", code, out):
                result["error"] = "git pull failed (conflict?)"
                return result

            code, out = _run(["push", "-q", "origin", branch], root)
            if not step("push", code, out):
                result["error"] = "git push failed"
                return result
            result["pushed"] = True
            result["ok"] = True
    except RuntimeError as exc:
        result["error"] = str(exc)
    finally:
        result["finished_at"] = _dt.datetime.now().isoformat(timespec="seconds")
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Commit and push every change in this repository.")
    parser.add_argument("--root", help="repository path (default: detect from this file)")
    parser.add_argument("-m", "--message", help="commit message")
    parser.add_argument("--status", action="store_true", help="print status JSON and exit")
    parser.add_argument("--json", action="store_true", help="print result as JSON")
    parser.add_argument("--quiet", action="store_true", help="print nothing unless an error occurs")
    args = parser.parse_args(argv)

    try:
        root = repo_root(Path(args.root).resolve() if args.root else None)
    except RuntimeError as exc:
        print(f"[gitsync] {exc}", file=sys.stderr)
        return 0

    if args.status:
        print(json.dumps(status(root), ensure_ascii=False, indent=2))
        return 0

    result = sync(root, args.message)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif not args.quiet:
        state = "ok" if result["ok"] else f"FAILED: {result.get('error')}"
        extra = result.get("message", "no changes")
        print(f"[gitsync] {state} ({extra})")
    elif not result["ok"]:
        print(f"[gitsync] FAILED: {result.get('error')}", file=sys.stderr)
    # Never block the caller (hook) on a sync failure.
    return 0


if __name__ == "__main__":
    sys.exit(main())
