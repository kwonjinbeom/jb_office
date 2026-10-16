"""블로그 RSS 읽기. 로그인 없이 공개 주소만 읽는다.

주소 규칙: 티스토리 <주소>/rss · 네이버 rss.blog.naver.com/<아이디>.xml · 블로거 <주소>/feeds/posts/default?alt=rss
PythonAnywhere 무료 계정은 허용 목록 밖 주소로 나갈 수 없다 (2026-10-16 확인: tistory·naver 없음).
막히면 예외를 내지 않고 FeedState 에 이유를 남긴다.
"""
import re
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone as dt_timezone
from email.utils import parsedate_to_datetime

from django.utils import timezone

from .models import FeedEntry, FeedState, Plan

TIMEOUT = 8
ATOM = "{http://www.w3.org/2005/Atom}"


def feed_url(blog) -> str:
    addr = (blog.address or "").strip().rstrip("/")
    if not addr:
        return ""
    if blog.platform == "naver":
        m = re.search(r"blog\.naver\.com/([A-Za-z0-9_\-]+)", addr)
        return f"https://rss.blog.naver.com/{m.group(1)}.xml" if m else ""
    if blog.platform == "tistory":
        return f"{addr}/rss"
    if blog.platform == "blogger":
        return f"{addr}/feeds/posts/default?alt=rss"
    if blog.platform == "wordpress":
        return f"{addr}/feed"
    return ""


def _date(text):
    text = (text or "").strip()
    if not text:
        return None
    try:
        d = parsedate_to_datetime(text)
    except (TypeError, ValueError):
        try:
            d = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            return None
    return d if d.tzinfo else d.replace(tzinfo=dt_timezone.utc)


def parse(xml_bytes: bytes) -> list[tuple[str, str, datetime]]:
    """RSS 2.0 과 Atom 둘 다. (제목, 주소, 발행 시각)"""
    root = ET.fromstring(xml_bytes)
    out = []
    for item in root.iter("item"):
        title, link = (item.findtext("title") or "").strip(), (item.findtext("link") or "").strip()
        when = _date(item.findtext("pubDate"))
        if title and link and when:
            out.append((title, link, when))
    for entry in root.iter(f"{ATOM}entry"):
        title = (entry.findtext(f"{ATOM}title") or "").strip()
        link_el = next((l for l in entry.findall(f"{ATOM}link") if l.get("rel", "alternate") == "alternate"), None)
        when = _date(entry.findtext(f"{ATOM}published") or entry.findtext(f"{ATOM}updated"))
        if title and link_el is not None and when:
            out.append((title, link_el.get("href", ""), when))
    return out


def _norm(title: str) -> str:
    return re.sub(r"\s+", "", title or "")


def _store(blog, items) -> int:
    """읽은 글을 저장하고, 같은 제목의 계획을 '발행'으로 바꾼다. 새로 찾은 글 수를 돌려준다."""
    added = 0
    plans = {_norm(p.title): p for p in Plan.objects.filter(blog=blog).exclude(status=Plan.Status.PUBLISHED)}
    for title, link, when in items:
        _, created = FeedEntry.objects.get_or_create(url=link, defaults={"blog": blog, "title": title[:300],
                                                                         "published_at": when})
        added += int(created)
        plan = plans.pop(_norm(title), None)
        if plan:
            plan.status, plan.url = Plan.Status.PUBLISHED, link
            plan.published_on = timezone.localtime(when).date()
            plan.save(update_fields=["status", "url", "published_on", "updated_at"])
    return added


def sync(blog, fetch=None) -> FeedState:
    state, _ = FeedState.objects.get_or_create(blog=blog)
    state.feed_url = feed_url(blog)
    state.checked_at = timezone.now()
    if not state.feed_url:
        state.ok, state.message = False, "주소가 없어 RSS 를 알 수 없어요"
        state.save()
        return state
    try:
        if fetch is not None:
            data = fetch(state.feed_url)
        else:
            req = urllib.request.Request(state.feed_url, headers={"User-Agent": "Mozilla/5.0 (JB Office RSS)"})
            with urllib.request.urlopen(req, timeout=TIMEOUT) as res:
                data = res.read()
        added = _store(blog, parse(data))
        state.ok, state.message = True, f"새 글 {added}편"
    except urllib.error.HTTPError as e:
        state.ok = False
        state.message = "서버에서 접속이 막혀 있어요 (PythonAnywhere 허용 목록)" if e.code in (403, 407) else f"RSS 응답 오류 {e.code}"
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        state.ok, state.message = False, f"서버에서 접속하지 못했어요 ({type(e).__name__})"
    except ET.ParseError:
        state.ok, state.message = False, "RSS 형식을 읽지 못했어요"
    state.save()
    return state
