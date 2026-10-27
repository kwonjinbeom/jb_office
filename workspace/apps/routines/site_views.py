"""사이트별·글별 조회수 받기 (2026-10-27 사용자: 화면 말고 명령 하나로 모든 사이트의 정밀한 조회·방문 통계).

GA4(구글 애널리틱스)에 사이트마다 속성 하나씩 두고, Data API 로 최근 N일 글별 조회수·날짜별 조회수·유입 경로를 받아
workspace/.routine/perf/ 에 쓴다 (search_perf 와 같은 폴더 · git 에 올리지 않는다). 인증은 search_perf 와 같은 토큰
(`manage.py search_perf --auth` 한 번에 서치 콘솔·애널리틱스 범위를 같이 받는다).

--setup: 서치 콘솔에 있는 사이트 중 GA4 속성이 없는 곳에 속성·웹 스트림을 만들고 측정 ID(G-…)를 알려 준다.
네이버 블로그는 GA4 코드를 넣을 수 없어 다루지 않는다 (운영 › 통계의 공개 숫자).
"""
import json
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, timedelta

from . import search_perf
from .search_perf import PerfError

ADMIN = "https://analyticsadmin.googleapis.com/v1beta"
DATA = "https://analyticsdata.googleapis.com/v1beta"
DAYS = 28
TOP = 10  # 명령 창에 사이트마다 보여 줄 글 수
PAGE_LIMIT = 1000
SERVER_DAYS = 90  # 통계현황 기간 (7·30·90일) 을 다 채운다
SERVER_PAGES = 50  # 통계현황 '많이 본 글'에 보낼 사이트마다 글 수 (최근 30일)


def _call(url, token, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method="POST" if body is not None else "GET",
                                 headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=search_perf.TIMEOUT) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")
        if e.code == 403 and "insufficient" in detail.lower():
            raise PerfError("애널리틱스 권한이 없는 토큰입니다. 다시 manage.py search_perf --auth") from e
        if e.code == 403 and ("has not been used" in detail or "disabled" in detail):
            raise PerfError("구글 클라우드 콘솔에서 'Google Analytics Admin API'·'Google Analytics Data API' 를 사용 설정하세요") from e
        raise


def host(url):
    """https://www.jinbaam.com/ · sc-domain:jinbaam.com → jinbaam.com"""
    h = (url or "").replace("sc-domain:", "").split("://")[-1].split("/")[0].lower()
    return h[4:] if h.startswith("www.") else h


def properties(token):
    """GA4 속성마다 웹 스트림 → [{"property", "account", "host", "measurement"}] (스트림 없는 속성은 host 가 빈칸)"""
    out, page = [], ""
    while True:
        res = _call(f"{ADMIN}/accountSummaries?pageSize=200" + (f"&pageToken={page}" if page else ""), token)
        for acc in res.get("accountSummaries", []):
            for prop in acc.get("propertySummaries", []):
                streams = _call(f"{ADMIN}/{prop['property']}/dataStreams", token).get("dataStreams", [])
                webs = [s for s in streams if s.get("type") == "WEB_DATA_STREAM"] or [{}]
                for s in webs:
                    web = s.get("webStreamData") or {}
                    out.append({"property": prop["property"], "account": acc.get("account", ""),
                                "host": host(web.get("defaultUri", "")), "measurement": web.get("measurementId", "")})
        page = res.get("nextPageToken", "")
        if not page:
            return out


def accounts(token):
    return [a.get("account") for a in _call(f"{ADMIN}/accountSummaries?pageSize=200", token).get("accountSummaries", [])]


def gsc_hosts(token):
    """서치 콘솔에 있는 사이트 (속성을 만들 대상)"""
    sites = search_perf._api("/sites", token).get("siteEntry", [])
    return list(dict.fromkeys(host(s["siteUrl"]) for s in sites if s.get("permissionLevel") != "siteUnverifiedUser"))


def setup(token=None):
    """서치 콘솔 사이트 중 GA4 웹 스트림이 없는 곳에 속성·스트림을 만든다 → [(host, 측정 ID, 새로 만듦)]"""
    token = token or search_perf.access_token()
    have = {p["host"]: p for p in properties(token) if p["host"]}
    accs = accounts(token)
    results = []
    for h in gsc_hosts(token):
        if h in have:
            results.append((h, have[h]["measurement"], False))
            continue
        if not accs:
            raise PerfError("GA4 계정이 없습니다: analytics.google.com 에서 '측정 시작'으로 계정을 하나 만드세요")
        prop = _call(f"{ADMIN}/properties", token, {"parent": accs[0], "displayName": h, "timeZone": "Asia/Seoul",
                                                     "currencyCode": "KRW"})
        stream = _call(f"{ADMIN}/{prop['name']}/dataStreams", token,
                       {"type": "WEB_DATA_STREAM", "displayName": h, "webStreamData": {"defaultUri": f"https://{h}"}})
        results.append((h, (stream.get("webStreamData") or {}).get("measurementId", ""), True))
    return results


def _report(prop, token, start, end, dims, metrics, order=None, limit=PAGE_LIMIT):
    body = {"dateRanges": [{"startDate": start.isoformat(), "endDate": end.isoformat()}],
            "dimensions": [{"name": d} for d in dims], "metrics": [{"name": m} for m in metrics], "limit": limit}
    if order:
        body["orderBys"] = [{"metric": {"metricName": order}, "desc": True}]
    rows = _call(f"{DATA}/{prop}:runReport", token, body).get("rows", [])
    return [[d.get("value", "") for d in r.get("dimensionValues", [])] + [_int(m.get("value")) for m in r.get("metricValues", [])]
            for r in rows]


def _int(v):
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return 0


def _fetch(prop, token, start, end):
    """속성 하나의 (글별 [경로, 제목, 조회, 사용자], 날짜별 [YYYYMMDD, 조회, 사용자, 세션], 유입 [경로, 세션])"""
    pages = _report(prop, token, start, end, ["pagePath", "pageTitle"], ["screenPageViews", "activeUsers"], order="screenPageViews")
    daily = sorted(_report(prop, token, start, end, ["date"], ["screenPageViews", "activeUsers", "sessions"]))
    channels = _report(prop, token, start, end, ["sessionDefaultChannelGroup"], ["sessions"], order="sessions")
    return pages, daily, channels


def collect(today=None, days=SERVER_DAYS):
    """통계현황으로 보낼 숫자 ('지금 수집'·발행 확인 때 PC 가 부른다, routines.local_run.check_feeds).
    인증·속성이 없거나 구글에 못 닿으면 빈 목록 — 나머지 수집은 그대로 간다.
    → [{"host", "daily": [[날짜, 조회, 사용자]], "pages": [[경로, 제목, 조회, 사용자]], "channels": [[경로, 세션]]}]"""
    today = today or date.today()
    start = today - timedelta(days=days - 1)
    try:
        token = search_perf.access_token()
        props = [p for p in properties(token) if p["host"]]
    except (PerfError, urllib.error.URLError, OSError, ValueError):
        return []
    out = []
    for p in props:
        try:
            daily = sorted(_report(p["property"], token, start, today, ["date"], ["screenPageViews", "activeUsers"]))
            s30 = today - timedelta(days=29)  # 글·유입은 최근 30일
            pages = _report(p["property"], token, s30, today, ["pagePath", "pageTitle"], ["screenPageViews", "activeUsers"],
                            order="screenPageViews", limit=SERVER_PAGES)
            channels = _report(p["property"], token, s30, today, ["sessionDefaultChannelGroup"], ["sessions"], order="sessions")
        except (PerfError, urllib.error.URLError, OSError, ValueError):
            continue
        out.append({"host": p["host"], "daily": [[f"{d[:4]}-{d[4:6]}-{d[6:]}", v, u] for d, v, u in daily],
                    "pages": pages, "channels": channels})
    return out


def pull(today=None, days=DAYS):
    """GA4 속성마다 글별·날짜별·유입 경로 CSV 와 조회수.md → [(host, 한 줄, 상위 글 [(조회, 사용자, 경로, 제목)])]"""
    today = today or date.today()
    start = today - timedelta(days=days - 1)
    token = search_perf.access_token()
    props = [p for p in properties(token) if p["host"]]
    if not props:
        raise PerfError("GA4 속성이 아직 없습니다: manage.py site_views --setup")
    search_perf.out_dir().mkdir(parents=True, exist_ok=True)
    results, md = [], [f"# 조회수 · {start} ~ {today} (GA4, 받은 날 {today})", ""]
    for p in props:
        h = p["host"]
        try:
            pages, daily, channels = _fetch(p["property"], token, start, today)
        except urllib.error.HTTPError as e:
            results.append((h, f"실패 (HTTP {e.code})", []))
            continue
        search_perf._write(search_perf.out_dir() / f"{h}_조회수_글.csv", ["경로", "제목", "조회수", "사용자"], pages)
        search_perf._write(search_perf.out_dir() / f"{h}_조회수_날짜.csv", ["날짜", "조회수", "사용자", "세션"],
                           [[f"{d[:4]}-{d[4:6]}-{d[6:]}", v, u, s] for d, v, u, s in daily])
        search_perf._write(search_perf.out_dir() / f"{h}_유입.csv", ["유입 경로", "세션"], channels)
        views, users = sum(r[1] for r in daily), sum(r[2] for r in daily)
        line = f"조회 {views} · 사용자 {users} · 글 {len(pages)}"
        if channels:
            line += " · 유입 " + ", ".join(f"{c} {n}" for c, n in channels[:4])
        top = [(v, u, path, title) for path, title, v, u in pages[:TOP]]
        results.append((h, line, top))
        md += [f"## {h} — {line}", "", "| 글 | 조회수 | 사용자 |", "|---|---|---|"]
        md += [f"| {title or path} ({path}) | {v} | {u} |" for v, u, path, title in top]
        md.append("")
    (search_perf.out_dir() / "조회수.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    return results


def snippet(measurement):
    """사이트 <head> 에 넣을 GA4 코드"""
    return (f'<script async src="https://www.googletagmanager.com/gtag/js?id={measurement}"></script>\n'
            "<script>window.dataLayer=window.dataLayer||[];function gtag(){dataLayer.push(arguments);}"
            f"gtag('js',new Date());gtag('config','{measurement}');</script>")
