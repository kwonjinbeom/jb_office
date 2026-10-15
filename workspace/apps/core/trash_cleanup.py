"""WSGI에서도 예약 작업 설정 없이 실행: 접근 시 최대 한 시간에 한 번, 50묶음씩 정리."""
import logging
import sys
import threading
import time

from django.conf import settings
from django.db import OperationalError, ProgrammingError
from django.utils import timezone

from .models import AppSetting
from .trash import purge_expired

_lock = threading.Lock()
_next_check = 0.0
logger = logging.getLogger(__name__)


def maybe_purge():
    global _next_check
    if not getattr(settings, "TRASH_CLEANUP_ENABLED", True) or "test" in sys.argv:
        return
    if time.monotonic() < _next_check or not _lock.acquire(blocking=False):
        return
    try:
        _next_check = time.monotonic() + 3600
        now = int(time.time())
        lease, _ = AppSetting.objects.get_or_create(key="trash_cleanup_lease", defaults={"value": "0"})
        try:
            last = int(lease.value)
        except ValueError:
            last = 0
        if now - last < 3600:
            return
        if AppSetting.objects.filter(pk=lease.pk, value=lease.value).update(value=str(now), updated_at=timezone.now()):
            purge_expired()
    except (OperationalError, ProgrammingError):
        # Initial installation/migration must not make the rest of the application unavailable.
        _next_check = time.monotonic() + 60
    except Exception:
        logger.exception("trash cleanup failed")
    finally:
        _lock.release()


class TrashCleanupMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if response.status_code < 400 and not request.path.startswith(("/static/", "/api/", "/deploy/")):
            maybe_purge()
        return response
