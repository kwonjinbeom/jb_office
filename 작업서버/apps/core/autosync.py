"""runserver 와 함께 도는 백그라운드 git 동기화 스레드.

- settings.AUTOSYNC["INTERVAL_SECONDS"] 마다 저장소를 확인한다.
- 변경 파일이 있거나 push 안 된 커밋이 있을 때만 동기화한다.
- 데몬 스레드라 서버가 꺼지면 같이 꺼진다.
"""
from __future__ import annotations

import logging
import threading

from django.conf import settings

from . import gitstate

log = logging.getLogger(__name__)

_thread: threading.Thread | None = None
_stop = threading.Event()


def _loop() -> None:
    interval = max(30, int(settings.AUTOSYNC["INTERVAL_SECONDS"]))
    log.info("autosync started (every %ss)", interval)
    while not _stop.wait(interval):
        try:
            st = gitstate.get_status()
            needs = st["dirty"] > 0 or (st.get("ahead") or 0) > 0
            if not needs:
                continue
            result = gitstate.run_sync(reason="auto")
            if result["ok"]:
                log.info("autosync ok: %s", result.get("message", "no changes"))
            else:
                log.warning("autosync failed: %s", result.get("error"))
        except Exception:  # 스레드가 죽지 않게 한다
            log.exception("autosync loop error")


def start_background_sync() -> None:
    global _thread
    if not settings.AUTOSYNC["ENABLED"]:
        log.info("autosync disabled by settings")
        return
    if _thread and _thread.is_alive():
        return
    _stop.clear()
    _thread = threading.Thread(target=_loop, name="git-autosync", daemon=True)
    _thread.start()


def is_running() -> bool:
    return bool(_thread and _thread.is_alive())
