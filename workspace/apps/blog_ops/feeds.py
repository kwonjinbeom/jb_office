"""블로그 RSS 읽기. 로그인 없이 공개 주소만 읽는다.

주소 규칙: 티스토리 <주소>/rss · 네이버 rss.blog.naver.com/<아이디>.xml · 블로거 <주소>/feeds/posts/default?alt=rss
PythonAnywhere 무료 계정은 허용 목록 밖 주소로 나갈 수 없다 (2026-10-16 확인: tistory·naver 없음).
그래서 모니터링의 '발행 확인'과 일일루틴 '전체 실행'은 PC 가 RSS 를 읽어 서버로 보낸다 (read → views.api_feeds → record).
막히면 예외를 내지 않고 FeedState 에 이유를 남긴다.

읽은 글과 제목이 같은 '넣은 곳'(그 사이트 카테고리에 넣은 미발행 글)은 발행 완료로 바꾼다 (auto_publish, 2026-10-22 사용자).
"""
import re
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone as dt_timezone
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
    """제목 견주기: 빈칸·따옴표·가운뎃점은 빼고 소문자로"""
    return re.sub(r"[\s\"'“”‘’·]", "", title or "").lower()


def _store(blog, items) -> int:
    """읽은 글을 저장하고, 같은 제목의 (예전) 발행 계획을 '발행'으로 바꾼다. 새로 찾은 글 수를 돌려준다."""
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


def _mark(post, when):
    if post is not None and not post.published_on:  # 발행일은 RSS 에 올라온 날
        post.published_on = timezone.localtime(when).date()
        post.save(update_fields=["published_on", "updated_at"])


def auto_publish(blog, items) -> int:
    """RSS 에 올라온 글과 제목(변환 제목 또는 글 제목)이 같은 이 사이트의 미발행 '넣은 곳'을 발행 완료로.
    넣은 곳이 모두 발행 완료면 글도 발행 완료 (sites.sync_post). 넣은 곳 없이 사이트만 이 사이트로 정한 발행예정글도.
    넣기(만들기) 하루 전보다 먼저 올라온 같은 제목의 옛 글로는 바꾸지 않는다. 바꾼 수를 돌려준다."""
    from apps.blog_types import sites
    from apps.blog_types.models import Placement
    from apps.naver_writing.models import Post as NaverPost
    from apps.writing.models import Post

    waiting = {}
    for pl in (Placement.objects.filter(site_category__blog=blog, status=Placement.Status.UNSAVED)
               .select_related("tistory_post", "naver_post")):
        post = pl.post
        for t in {pl.converted_title, post.title if post else ""}:
            if t.strip():
                waiting.setdefault(_norm(t), []).append(pl)
    alone = {}
    for model in (Post, NaverPost):
        for post in model.objects.filter(stage="post", publish_status=model.Publish.TODO, target=blog.name, placements__isnull=True):
            alone.setdefault(_norm(post.title), []).append(post)
    done = 0
    for title, _link, when in items:
        key = _norm(title)
        for pl in waiting.pop(key, []):
            if pl.status != Placement.Status.UNSAVED or when < pl.created_at - timedelta(days=1):
                continue
            pl.status = Placement.Status.PUBLISHED
            pl.save(update_fields=["status", "updated_at"])
            _mark(pl.post, when)
            if pl.post is not None:
                sites.sync_post(pl.post)
            done += 1
        for post in alone.pop(key, []):
            if when < post.created_at - timedelta(days=1):
                continue
            _mark(post, when)
            sites.publish(post, True)
            done += 1
    return done


def read(url, fetch=None, where="서버"):
    """RSS 주소 하나 → (읽었나, 이유, [(제목, 주소, 시각)]). where: 이유 문구에 쓸 읽은 곳 (서버 · PC)."""
    if not url:
        return False, "주소가 없어 RSS 를 알 수 없어요", []
    try:
        if fetch is not None:
            data = fetch(url)
        else:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (JB Office RSS)"})
            with urllib.request.urlopen(req, timeout=TIMEOUT) as res:
                data = res.read()
        return True, "", parse(data)
    except urllib.error.HTTPError as e:
        blocked = e.code in (403, 407) and where == "서버"
        return False, "서버에서 접속이 막혀 있어요 (PythonAnywhere 허용 목록)" if blocked else f"RSS 응답 오류 {e.code}", []
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        return False, f"{where}에서 접속하지 못했어요 ({type(e).__name__})", []
    except ET.ParseError:
        return False, "RSS 형식을 읽지 못했어요", []


def record(blog, ok, message, items, where="서버") -> FeedState:
    """읽은 결과를 남긴다: 글 저장 · 발행 완료 자동 처리 · 마지막 확인."""
    state, _ = FeedState.objects.get_or_create(blog=blog)
    state.feed_url = feed_url(blog)
    state.checked_at = timezone.now()
    state.ok = ok
    if ok:
        added, published = _store(blog, items), auto_publish(blog, items)
        state.message = f"{where} 확인 · 새 글 {added}편" + (f" · 발행 완료 {published}건" if published else "")
    else:
        state.message = message[:200]
    state.save()
    return state


def sync(blog, fetch=None) -> FeedState:
    return record(blog, *read(feed_url(blog), fetch))
