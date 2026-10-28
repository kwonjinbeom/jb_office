"""PC 터미널에 줄 안내문을 서버에도 잠깐 둔다 (2026-10-27 애니 총정리 → 2026-10-28 사이트 변환도).

화면은 안내문을 클립보드에 복사하고 jbroutine: 링크로 PC 를 깨운다. 브라우저가 복사를 거절하거나(서버가 안내문을 만드는 사이
창 초점이 바뀜) PC 가 클립보드에서 못 찾으면, PC 실행기(routines/local_run)가 링크의 key 로 서버에서 받아 간다.
자리(slot)마다 마지막 안내문 하나 {key, prompt, at} — 30분 안에 한 번만 준다.
"""
import hmac
import json
import secrets
from datetime import datetime, timedelta

from django.utils import timezone

from .models import AppSetting

TTL = timedelta(minutes=30)


def keep(slot, prefix, prompt):
    """안내문을 두고 key 를 돌려준다. key 는 받아 가는 열쇠라 짐작 못 하게 (파일 이름에도 쓴다)."""
    key = f"{prefix}-{secrets.token_hex(10)}"
    AppSetting.set(slot, json.dumps({"key": key, "prompt": prompt, "at": timezone.now().isoformat()}, ensure_ascii=False))
    return key


def take(slot, key):
    """key 가 맞고 30분 안이면 안내문을 주고 지운다. 아니면 None."""
    try:
        saved = json.loads(AppSetting.get(slot) or "{}")
        fresh = timezone.now() - datetime.fromisoformat(saved["at"]) < TTL
    except (ValueError, KeyError):
        return None
    if not fresh or not hmac.compare_digest(key, saved.get("key", "")):
        return None
    AppSetting.objects.filter(key=slot).delete()
    return saved["prompt"]
