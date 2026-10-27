"""통계현황 (2026-10-23 사용자): 사이트별 방문자 · 공감 · 댓글 추이.

수집: 서버(PythonAnywhere 무료)는 티스토리·네이버에 못 나가서, '발행 확인'·'지금 수집'·일일루틴 '전체 실행' 때
PC 가 RSS 와 같이 읽어 보낸다 (routines/local_run.check_feeds → views.api_feeds → record). 로그인 없이 공개된 숫자만 GET 으로 읽는다
(티스토리 공감 주소 /reaction 은 POST 하면 공감이 눌린다 — 절대 POST 하지 않는다).
- 네이버: 방문자는 모바일 블로그 정보(오늘 방문자 · 누적), 공감·댓글은 모바일 글 목록의 최근 글 30편 합계.
  예전 방문자 그래프(NVisitorgp4Ajax)는 2026-10-24 확인 때 빈 응답(204)이었다 — 오늘 숫자만 오고, 어제는 누적으로 마저 채운다.
- 티스토리: 방문자는 스킨의 숨은 칸 `#jb-stat`(애니환산기/스킨에_붙일것.html), 없으면 스킨 사이드바의 'Today : n · Yesterday : n'.
  공감·댓글은 RSS 의 최근 글마다 공개 주소(GET /reaction?entryId= · /m/api/<글>/comment)로 합계 (2026-10-24 마저 개발).
- 블로거: 댓글은 공개 피드(alt=json)의 글마다 댓글 수 합계. 공감은 없다.
- 워드프레스: 댓글은 공개 REST(wp-json/wp/v2/comments)의 수, 공감은 없다 (2026-10-26).
공감·댓글 합계는 최근 글 범위의 합이라, 그날 공감·댓글 = 오늘 합계 − 앞 수집 합계 (줄면 0).
- GA4 (2026-10-27): 티스토리·블로거·워드프레스는 같은 PC 실행에서 GA4 날짜별 사용자(= 방문자)·조회, 최근 30일 많이 본 글·유입을
  받는다 (routines.site_views.collect → record_ga4). GA4 가 채운 날은 위 공개 숫자가 방문자를 덮지 않는다. 네이버는 GA4 를 못 붙여 공개 숫자만.
"""
import json
import re
import urllib.error
from collections import Counter
import urllib.request
from datetime import date, timedelta

from django.utils import timezone

TIMEOUT = 8
UA = "Mozilla/5.0 (JB Office stats)"
NAVER_VISIT = "https://blog.naver.com/NVisitorgp4Ajax.naver?blogId={id}"
NAVER_POSTS = "https://m.blog.naver.com/api/blogs/{id}/post-list?categoryNo=0&itemCount=30&page=1"
NAVER_INFO = "https://m.blog.naver.com/api/blogs/{id}"  # dayVisitorCount(오늘) · totalVisitorCount(누적)
TISTORY_LIKES = "{addr}/reaction?entryId={id}"  # GET 만 (POST 는 공감을 누른다)
TISTORY_COMMENTS = "{addr}/m/api/{id}/comment?reverse=true"
BLOGGER_FEED = "{addr}/feeds/posts/default?alt=json&max-results=30"
WP_COMMENTS = "{addr}/wp-json/wp/v2/comments?per_page=100&_fields=id"
RECENT = 20  # 티스토리 공감·댓글을 볼 최근 글 수 (글마다 두 번 읽는다)
# 사이트 색: 운영 화면의 사이트 순서대로 고정 (거른 뒤에도 색이 바뀌지 않게). dataviz 기본 범주 색 1~8.
COLORS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]


def naver_id(blog):
    m = re.search(r"blog\.naver\.com/([A-Za-z0-9_\-]+)", blog.address or "")
    return m.group(1) if m else ""


def target(blog):
    """PC 에 넘길 수집 대상 한 줄"""
    return {"blog": blog.pk, "name": blog.name, "platform": blog.platform, "address": (blog.address or "").rstrip("/"),
            "naver": naver_id(blog) if blog.platform == "naver" else ""}


def _get(url, referer="", fetch=None):
    if fetch is not None:
        return fetch(url)
    headers = {"User-Agent": UA}
    if referer:
        headers["Referer"] = referer
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=TIMEOUT) as res:
        return res.read()


def _num(text):
    digits = re.sub(r"[^0-9]", "", str(text or ""))
    return int(digits) if digits else None


def naver_visitors(xml):
    """<visitorcnt id="20261023" cnt="12"/> … → {"2026-10-23": 12}"""
    out = {}
    for d, n in re.findall(r'<visitorcnt[^>]*\bid="(\d{8})"[^>]*\bcnt="(\d+)"', xml.decode("utf-8", "replace")):
        out[f"{d[:4]}-{d[4:6]}-{d[6:]}"] = int(n)
    return out


def naver_totals(body):
    items = (json.loads(body.decode("utf-8")).get("result") or {}).get("items") or []
    likes = sum(_num(i.get("sympathyCnt")) or 0 for i in items)
    comments = sum(_num(i.get("commentCnt")) or 0 for i in items)
    return (likes, comments) if items else (None, None)


def naver_info(body):
    """모바일 블로그 정보 → (오늘 방문자, 누적 방문자). 없으면 (None, None)"""
    info = json.loads(body.decode("utf-8")).get("result") or {}
    return _num(info.get("dayVisitorCount")), _num(info.get("totalVisitorCount"))


def _skin_counts(text):
    """스킨 사이드바의 방문자 칸 (티스토리 기본 스킨들): 'Today : 1' · 'Yesterday : 3' · 'Total' 다음 숫자"""
    plain = re.sub(r"<[^>]+>", " ", text)
    out = {}
    for key, pat in (("today", r"(?:Today|오늘)\s*[:：]?\s*([\d,]+)"), ("yesterday", r"(?:Yesterday|어제)\s*[:：]?\s*([\d,]+)"),
                     ("total", r"(?:Total|전체|누적)\s*[:：]?\s*([\d,]+)")):
        m = re.search(pat, plain)
        if m:
            out[key] = m.group(1)
    return out if "today" in out else {}


def tistory_visitors(html, today):
    """스킨 조각의 <div id="jb-stat" data-today=".." data-yesterday=".."> → {오늘: n, 어제: n, "total": 누적}.
    조각이 없으면 스킨 사이드바의 'Today : n · Yesterday : n'. 둘 다 없으면 None"""
    text = html.decode("utf-8", "replace")
    tag = re.search(r'<[^>]*\bid="jb-stat"[^>]*>', text)
    attr = dict(re.findall(r'data-(today|yesterday|total)="([^"]*)"', tag.group(0))) if tag else _skin_counts(text)
    if not attr:
        return None
    out = {}
    if _num(attr.get("today")) is not None:
        out[today.isoformat()] = _num(attr["today"])
    if _num(attr.get("yesterday")) is not None:
        out[(today - timedelta(days=1)).isoformat()] = _num(attr["yesterday"])
    if _num(attr.get("total")) is not None:
        out["total"] = _num(attr["total"])
    return out


def tistory_entries(rss):
    """RSS 의 최근 글 번호 (<comments>…#entry11comment 또는 <guid>…/11)"""
    text = rss.decode("utf-8", "replace")
    ids = re.findall(r"#entry(\d+)comment", text) or re.findall(r"<guid>[^<]*/(\d+)</guid>", text)
    return list(dict.fromkeys(ids))[:RECENT]


def tistory_totals(addr, ids, fetch=None):
    """글마다 공감(GET /reaction) · 댓글(GET /m/api/<글>/comment) 수의 합. 한 글이 안 열려도 나머지는 센다."""
    likes = comments = seen = 0
    for i in ids:
        ref = f"{addr}/{i}"
        try:
            react = json.loads(_get(TISTORY_LIKES.format(addr=addr, id=i), ref, fetch).decode("utf-8"))
            cmt = json.loads(_get(TISTORY_COMMENTS.format(addr=addr, id=i), ref, fetch).decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, OSError, ValueError):
            continue
        likes += _num(((react.get("data") or {}).get("reactionCounter") or {}).get("sum")) or 0
        comments += _num((cmt.get("data") or {}).get("totalItems")) or 0
        seen += 1
    return (likes, comments) if seen else (None, None)


def blogger_comments(body):
    """블로거 공개 피드(alt=json)의 글마다 댓글 수(thr$total) 합. 글이 없으면 None"""
    entries = (json.loads(body.decode("utf-8")).get("feed") or {}).get("entry") or []
    return sum(_num((e.get("thr$total") or {}).get("$t")) or 0 for e in entries) if entries else None


def collect(site, fetch=None, today=None):
    """PC 에서 사이트 하나의 공개 숫자를 읽는다 → {"blog", "ok", "message", "visitors": {날짜: n}, "likes_total", "comments_total"}"""
    today = today or timezone.localdate()
    out = {"blog": site.get("blog"), "ok": False, "message": "", "visitors": {}, "visitors_total": None,
           "likes_total": None, "comments_total": None}
    addr = site.get("address") or ""
    try:
        if site.get("platform") == "naver" and site.get("naver"):
            nid = site["naver"]
            day_n, total = naver_info(_get(NAVER_INFO.format(id=nid), f"https://m.blog.naver.com/{nid}", fetch))
            if day_n is not None:
                out["visitors"] = {today.isoformat(): day_n}
                out["visitors_total"] = total
            out["likes_total"], out["comments_total"] = naver_totals(
                _get(NAVER_POSTS.format(id=nid), f"https://m.blog.naver.com/{nid}", fetch))
        elif site.get("platform") == "tistory" and addr:
            found = tistory_visitors(_get(addr + "/", "", fetch), today)
            if found is not None:
                out["visitors_total"] = found.pop("total", None)
                out["visitors"] = found
            out["likes_total"], out["comments_total"] = tistory_totals(addr, tistory_entries(_get(addr + "/rss", "", fetch)), fetch)
            if found is None and out["likes_total"] is None:
                out["message"] = "스킨에 방문자 칸이 없어요 (스킨에_붙일것.html 을 붙이면 방문자를 읽어요)"
                return out
        elif site.get("platform") == "blogger" and addr:
            out["comments_total"] = blogger_comments(_get(BLOGGER_FEED.format(addr=addr), "", fetch))
            out["likes_total"] = 0 if out["comments_total"] is not None else None  # 블로거는 공감이 없다
        elif site.get("platform") == "wordpress" and addr:
            out["comments_total"] = len(json.loads(_get(WP_COMMENTS.format(addr=addr.rstrip("/")), "", fetch).decode("utf-8")))
            out["likes_total"] = 0  # 워드프레스는 공감이 없다
        else:
            out["message"] = "공개된 숫자가 없어요"
            return out
    except urllib.error.HTTPError as e:
        out["message"] = f"응답 오류 {e.code}"
        return out
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        out["message"] = f"PC에서 접속하지 못했어요 ({type(e).__name__})"
        return out
    except ValueError:
        out["message"] = "숫자를 읽지 못했어요 (형식이 바뀌었을 수 있어요)"
        return out
    out["ok"] = bool(out["visitors"]) or out["likes_total"] is not None or out["comments_total"] is not None
    parts = [f"방문자 {len(out['visitors'])}일치"] if out["visitors"] else []
    if site.get("platform") in ("blogger", "wordpress"):
        parts.append("댓글 · 방문자는 GA4" if out["comments_total"] is not None else "방문자는 GA4")
    elif out["likes_total"] is not None:
        parts.append("공감·댓글")
    if site.get("platform") == "tistory" and not out["visitors"]:
        parts.append("스킨에 방문자 칸 없음")
    out["message"] = " · ".join(parts) or "읽은 숫자가 없어요"
    return out


def _fill_yesterday(blog, result, today):
    """누적 방문자로 어제를 마저 채운다 (네이버는 오늘 숫자만 준다).
    어제 마지막 수집 때 (누적 − 그때까지 어제 방문자) = 어제 시작, 지금 (누적 − 오늘 방문자) = 오늘 시작 → 차이가 어제 하루."""
    from .models import SiteStat
    total, today_n = result.get("visitors_total"), (result.get("visitors") or {}).get(today.isoformat())
    if not isinstance(total, int) or not isinstance(today_n, int):
        return
    row, _ = SiteStat.objects.get_or_create(blog=blog, day=today)
    row.visitors_total = total
    row.save(update_fields=["visitors_total", "updated_at"])
    prev = SiteStat.objects.filter(blog=blog, day=today - timedelta(days=1)).first()
    if ((today - timedelta(days=1)).isoformat() in (result.get("visitors") or {}) or prev is None or prev.hand
            or prev.views is not None or prev.visitors is None or prev.visitors_total is None):
        return
    full = (total - today_n) - (prev.visitors_total - prev.visitors)
    if full >= prev.visitors:
        prev.visitors = full
        prev.save(update_fields=["visitors", "updated_at"])


def record(blog, result, today=None):
    """PC 가 읽은 숫자를 남긴다. 직접 넣은 날(hand)은 덮어쓰지 않는다. 사이트의 수집 상태도."""
    from .models import FeedState, SiteStat
    today = today or timezone.localdate()
    for key, n in (result.get("visitors") or {}).items():
        try:
            day = date.fromisoformat(key)
        except ValueError:
            continue
        if not isinstance(n, int) or n < 0 or day > today:
            continue
        row, _ = SiteStat.objects.get_or_create(blog=blog, day=day)
        if not row.hand and row.views is None:  # GA4 가 채운 날은 GA4 숫자를 둔다
            row.visitors = n
            row.save(update_fields=["visitors", "updated_at"])
    _fill_yesterday(blog, result, today)
    lt, ct = result.get("likes_total"), result.get("comments_total")
    if isinstance(lt, int) and isinstance(ct, int):
        row, _ = SiteStat.objects.get_or_create(blog=blog, day=today)
        prev = (SiteStat.objects.filter(blog=blog, day__lt=today, likes_total__isnull=False)
                .order_by("-day").first())
        row.likes_total, row.comments_total = lt, ct
        if not row.hand and prev is not None:
            row.likes, row.comments = max(0, lt - prev.likes_total), max(0, ct - (prev.comments_total or 0))
        row.save()
    state, _ = FeedState.objects.get_or_create(blog=blog)
    state.stat_checked_at, state.stat_ok = timezone.now(), bool(result.get("ok"))
    state.stat_message = str(result.get("message") or "")[:200]
    state.save(update_fields=["stat_checked_at", "stat_ok", "stat_message"])
    return state


def ga4_blogs(blogs):
    """GA4 가 보내는 host(jinbaam.tistory.com) → 사이트"""
    from apps.routines.site_views import host
    return {host(b.address): b for b in blogs if b.address}


def record_ga4(blog, r, today=None):
    """PC 가 받은 GA4 숫자: 날짜별 조회·사용자(= 방문자), 최근 30일 글별 조회, 유입. 직접 넣은 날은 그대로."""
    from .models import FeedState, SiteStat, SitePage
    today = today or timezone.localdate()
    days = 0
    for row in r.get("daily") or []:
        try:
            day, views, users = date.fromisoformat(row[0]), int(row[1]), int(row[2])
        except (TypeError, ValueError, IndexError):
            continue
        if day > today or views < 0 or users < 0:
            continue
        stat, _ = SiteStat.objects.get_or_create(blog=blog, day=day)
        stat.views = views
        if not stat.hand:
            stat.visitors = users
        stat.save(update_fields=["views", "visitors", "updated_at"])
        days += 1
    pages = []
    for row in r.get("pages") or []:
        try:
            pages.append(SitePage(blog=blog, path=str(row[0])[:500], title=str(row[1])[:300], views=int(row[2]), users=int(row[3])))
        except (TypeError, ValueError, IndexError):
            continue
    SitePage.objects.filter(blog=blog).delete()
    SitePage.objects.bulk_create(pages)
    state, _ = FeedState.objects.get_or_create(blog=blog)
    state.ga_checked_at = timezone.now()
    state.ga_channels = [[str(c[0]), _num(c[1]) or 0] for c in r.get("channels") or [] if isinstance(c, list) and len(c) == 2]
    state.save(update_fields=["ga_checked_at", "ga_channels"])
    return f"GA4 {days}일 · 글 {len(pages)}"


# ---------------------------------------------------------------------------
# 화면
# ---------------------------------------------------------------------------
def color_of(blog, order):
    return COLORS[order.index(blog.pk) % len(COLORS)] if blog.pk in order else COLORS[-1]


def _nice(top):
    """y 축 위 끝 (4 칸으로 나눈다): 눈금이 7·15·22 처럼 끊기지 않게 4 로 나눠떨어지는 값.
    40 까지는 4 의 배수, 그 위는 1 · 1.2 · 1.6 · 2 · 2.4 · 3.2 · 4 · 4.8 · 6 · 8 × 10^n 중 top 이상인 가장 작은 값"""
    if top <= 40:
        return max(4, -(-int(top + 0.999) // 4) * 4)
    step = 10 ** (len(str(int(top))) - 1)
    for k in (1, 1.2, 1.6, 2, 2.4, 3.2, 4, 4.8, 6, 8, 10):
        if k * step >= top:
            return int(k * step)
    return int(10 * step)


def chart(series, days, width=960, height=260):
    """여러 사이트 꺾은선 (같은 축 하나). series: [{"name", "color", "values": [n|None]}] → 그릴 좌표."""
    pad_l, pad_r, pad_t, pad_b = 44, 16, 14, 28
    w, h = width - pad_l - pad_r, height - pad_t - pad_b
    top = _nice(max([v for s in series for v in s["values"] if v is not None] or [0]))
    n = len(days)
    x = [pad_l + (w * i / (n - 1) if n > 1 else w / 2) for i in range(n)]
    lines = []
    for s in series:
        pts = [(round(x[i], 1), round(pad_t + h - h * v / top, 1)) for i, v in enumerate(s["values"]) if v is not None]
        # 빈 날은 선을 끊는다
        segs, cur = [], []
        for i, v in enumerate(s["values"]):
            if v is None:
                if cur:
                    segs.append(cur)
                cur = []
            else:
                cur.append(f"{x[i]:.1f},{pad_t + h - h * v / top:.1f}")
        if cur:
            segs.append(cur)
        lines.append({**s, "segs": [" ".join(c) for c in segs], "dots": pts if n <= 14 else [],
                      "end": pts[-1] if pts else None})
    every = 1 if n <= 10 else (5 if n <= 35 else 14)
    xlabels = [(round(x[i], 1), d) for i, d in enumerate(days) if (n - 1 - i) % every == 0]
    grid = [(round(pad_t + h - h * k / 4, 1), int(top * k / 4)) for k in range(5)]
    cols = [{"x": round(x[i], 1), "day": d, "left": round(x[i] - (w / max(n - 1, 1)) / 2, 1),
             "w": round(w / max(n - 1, 1), 1),
             "vals": [(s["name"], s["color"], s["values"][i]) for s in series]} for i, d in enumerate(days)]
    return {"width": width, "height": height, "lines": lines, "xlabels": xlabels, "grid": grid, "cols": cols,
            "plot": {"l": pad_l, "r": width - pad_r, "t": pad_t, "b": pad_t + h, "h": h}}


def spark(values, width=120, height=32):
    vals = [v for v in values if v is not None]
    if len(vals) < 2:
        return ""
    top, n = max(vals) or 1, len(values)
    pts = [f"{width * i / (n - 1):.1f},{height - 2 - (height - 4) * v / top:.1f}" for i, v in enumerate(values) if v is not None]
    return " ".join(pts)


CHANNELS = {"Organic Search": "검색", "Direct": "직접", "Referral": "다른 사이트", "Organic Social": "SNS", "Unassigned": "알 수 없음",
            "Paid Search": "검색 광고", "Email": "메일", "Organic Video": "동영상", "Display": "광고", "Organic Shopping": "쇼핑"}
TOP_PAGES = 10


def _sum(vals):
    got = [v for v in vals if v is not None]
    return sum(got) if got else None


def page_data(blogs, all_order, days, today):
    """통계현황 화면 (2026-10-27 사용자: 보기 편하게 싹 갈아엎기).
    사이트 칸(기간 방문자 · 어제·오늘 · 조회·공감·댓글) → 하루 방문자 꺾은선 → 많이 본 글 · 어디서 왔나."""
    from .models import FeedState, SitePage, SiteStat
    rows = {(r.blog_id, r.day): r for r in SiteStat.objects.filter(blog__in=blogs, day__range=(days[0], days[-1]))}
    states = {s.blog_id: s for s in FeedState.objects.filter(blog__in=blogs)}
    yday = today - timedelta(days=1)
    tiles, series = [], []
    for b in blogs:
        vals = {m: [getattr(rows.get((b.pk, d)), m, None) for d in days] for m in ("visitors", "views", "likes", "comments")}
        color = color_of(b, all_order)
        state = states.get(b.pk)
        tiles.append({"blog": b, "color": color, "visitors": _sum(vals["visitors"]), "views": _sum(vals["views"]),
                      "likes": _sum(vals["likes"]), "comments": _sum(vals["comments"]),
                      "today": getattr(rows.get((b.pk, today)), "visitors", None),
                      "yesterday": getattr(rows.get((b.pk, yday)), "visitors", None),
                      "spark": spark(vals["visitors"]),
                      "source": "GA4" if _sum(vals["views"]) is not None else ("공개 숫자" if _sum(vals["visitors"]) is not None else ""),
                      "state": state})
        series.append({"name": b.name, "color": color, "values": vals["visitors"]})
    total = {k: _sum([t[k] for t in tiles]) for k in ("visitors", "views", "today", "yesterday")}
    total["spark"] = spark([_sum(col) for col in zip(*[s["values"] for s in series])] if series else [])
    colors = {t["blog"].pk: t["color"] for t in tiles}
    top = []
    for p in SitePage.objects.filter(blog__in=blogs).select_related("blog")[:TOP_PAGES]:
        top.append({"blog": p.blog, "color": colors.get(p.blog_id), "title": p.title or p.path, "views": p.views,
                    "url": (p.blog.address or "").rstrip("/") + p.path})
    counts = Counter()
    for s in states.values():
        for name, n in s.ga_channels or []:
            counts[CHANNELS.get(name, name)] += n
    whole = sum(counts.values())
    channels = [{"name": name, "n": n, "pct": round(n * 100 / whole), "color": COLORS[i % len(COLORS)]}
                for i, (name, n) in enumerate(counts.most_common(6))] if whole else []
    return {"tiles": tiles, "total": total, "chart": chart(series, days, height=420), "top": top, "channels": channels,
            "has_data": total["visitors"] is not None}
