"""우리 글의 검색 성과 받기 (2026-10-26 사용자: 남의 상위 글만 배우면 그 평균이 된다 — 우리 글 성과로 배운다).

구글 서치 콘솔 API 로 서치 콘솔에 있는 모든 사이트(memorily·눈잎·밤밤)의 최근 28일 글×검색어를 받아
workspace/.routine/perf/ 에 쓴다 (git 에 올리지 않는다: 저장소가 공개라 검색어 실적은 올리지 않는다). 프롬프트 최신화가 읽는다.

인증은 데스크톱 OAuth 한 번 (`manage.py search_perf --auth`): workspace/.env 의 GSC_CLIENT_ID · GSC_CLIENT_SECRET 로
브라우저 동의 → 갱신 토큰을 workspace/.routine/gsc_token.json 에. 설정 방법은 콘텐츠/블로그_카페/데이터/README.md '검색 성과'.
네이버는 API 가 없어 여기서 다루지 않는다 (운영 › 통계).
"""
import csv
import http.server
import json
import os
import secrets
import threading
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from datetime import date, timedelta
from pathlib import Path

from django.conf import settings

SCOPE = "https://www.googleapis.com/auth/webmasters.readonly"
AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
API = "https://www.googleapis.com/webmasters/v3"
TIMEOUT = 20
DAYS = 28
LAG = 3  # 서치 콘솔은 2~3일 늦게 채워진다
ROW_LIMIT = 5000


class PerfError(Exception):
    pass


def routine_dir() -> Path:
    return settings.BASE_DIR / ".routine"


def token_path() -> Path:
    return routine_dir() / "gsc_token.json"


def out_dir() -> Path:
    return routine_dir() / "perf"


def _client():
    cid, secret = os.environ.get("GSC_CLIENT_ID", "").strip(), os.environ.get("GSC_CLIENT_SECRET", "").strip()
    if not cid or not secret:
        raise PerfError("GSC_CLIENT_ID · GSC_CLIENT_SECRET 가 workspace/.env 에 없습니다 (데이터/README.md '검색 성과')")
    return cid, secret


def _post_form(url, fields):
    data = urllib.parse.urlencode(fields).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return json.loads(r.read().decode("utf-8"))


def _api(path, token, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(f"{API}{path}", data=data, method="POST" if body is not None else "GET",
                                 headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return json.loads(r.read().decode("utf-8"))


def authorize(open_browser=True, port=0):
    """한 번만: 브라우저 동의 → 갱신 토큰 저장. 저장한 경로를 돌려준다."""
    cid, secret = _client()
    state, got = secrets.token_urlsafe(16), {}

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            q = dict(urllib.parse.parse_qsl(urllib.parse.urlparse(self.path).query))
            if q.get("state") == state:
                got.update(q)
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write("JB Office: 허용을 받았습니다. 이 창을 닫아도 됩니다.".encode())

        def log_message(self, *args):
            pass

    server = http.server.HTTPServer(("127.0.0.1", port), Handler)
    redirect = f"http://127.0.0.1:{server.server_port}"
    url = AUTH_URL + "?" + urllib.parse.urlencode({"client_id": cid, "redirect_uri": redirect, "response_type": "code", "scope": SCOPE,
                                                   "access_type": "offline", "prompt": "consent", "state": state})
    print(f"브라우저에서 허용해 주세요:\n{url}")
    if open_browser:
        webbrowser.open(url)
    thread = threading.Thread(target=server.handle_request, daemon=True)
    thread.start()
    thread.join(timeout=300)
    server.server_close()
    if "code" not in got:
        raise PerfError("5분 안에 허용을 받지 못했습니다" + (f" ({got['error']})" if "error" in got else ""))
    tok = _post_form(TOKEN_URL, {"code": got["code"], "client_id": cid, "client_secret": secret, "redirect_uri": redirect,
                                 "grant_type": "authorization_code"})
    if not tok.get("refresh_token"):
        raise PerfError("갱신 토큰을 받지 못했습니다. 다시 --auth 하세요")
    routine_dir().mkdir(parents=True, exist_ok=True)
    token_path().write_text(json.dumps({"refresh_token": tok["refresh_token"]}), encoding="utf-8")
    return token_path()


def access_token():
    if not token_path().is_file():
        raise PerfError("아직 인증 전입니다: manage.py search_perf --auth")
    cid, secret = _client()
    refresh = json.loads(token_path().read_text(encoding="utf-8")).get("refresh_token", "")
    tok = _post_form(TOKEN_URL, {"refresh_token": refresh, "client_id": cid, "client_secret": secret, "grant_type": "refresh_token"})
    if not tok.get("access_token"):
        raise PerfError("토큰을 새로 받지 못했습니다. 다시 --auth 하세요")
    return tok["access_token"]


def _name(site_url):
    """https://nunip.tistory.com/ → nunip.tistory.com · sc-domain:x.com → x.com"""
    return site_url.replace("sc-domain:", "").split("://")[-1].strip("/").replace("/", "_") or "site"


def pull(today=None):
    """사이트마다 글×검색어 CSV 와 글별 합계 CSV, 그리고 한눈에 보는 summary.md. [(사이트, 한 줄)]"""
    today = today or date.today()
    end = today - timedelta(days=LAG)
    start = end - timedelta(days=DAYS - 1)
    token = access_token()
    sites = [s["siteUrl"] for s in _api("/sites", token).get("siteEntry", []) if s.get("permissionLevel") != "siteUnverifiedUser"]
    out_dir().mkdir(parents=True, exist_ok=True)
    results, summary = [], [f"# 검색 성과 · {start} ~ {end} (구글 서치 콘솔, 받은 날 {today})", ""]
    for site in sites:
        enc = urllib.parse.quote(site, safe="")
        base = {"startDate": start.isoformat(), "endDate": end.isoformat(), "rowLimit": ROW_LIMIT}
        try:
            pq = _api(f"/sites/{enc}/searchAnalytics/query", token, {**base, "dimensions": ["page", "query"]}).get("rows", [])
            pages = _api(f"/sites/{enc}/searchAnalytics/query", token, {**base, "dimensions": ["page"]}).get("rows", [])
        except urllib.error.HTTPError as e:
            results.append((site, f"실패 (HTTP {e.code})"))
            continue
        name = _name(site)
        _write(out_dir() / f"{name}.csv", ["글", "검색어", "클릭", "노출", "CTR(%)", "평균 순위"],
               [[r["keys"][0], r["keys"][1], r.get("clicks", 0), r.get("impressions", 0), round(r.get("ctr", 0) * 100, 1),
                 round(r.get("position", 0), 1)] for r in pq])
        pages.sort(key=lambda r: -r.get("impressions", 0))
        _write(out_dir() / f"{name}_글.csv", ["글", "클릭", "노출", "CTR(%)", "평균 순위"],
               [[r["keys"][0], r.get("clicks", 0), r.get("impressions", 0), round(r.get("ctr", 0) * 100, 1), round(r.get("position", 0), 1)]
                for r in pages])
        clicks, imps = sum(r.get("clicks", 0) for r in pages), sum(r.get("impressions", 0) for r in pages)
        results.append((site, f"글 {len(pages)} · 노출 {imps} · 클릭 {clicks}"))
        summary += [f"## {site} — 노출 {imps} · 클릭 {clicks} · 글 {len(pages)}", "", "| 글 | 노출 | 클릭 | 평균 순위 |", "|---|---|---|---|"]
        summary += [f"| {r['keys'][0]} | {r.get('impressions', 0)} | {r.get('clicks', 0)} | {round(r.get('position', 0), 1)} |" for r in pages[:15]]
        summary.append("")
    (out_dir() / "summary.md").write_text("\n".join(summary) + "\n", encoding="utf-8")
    return results


def _write(path, head, rows):
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(head)
        w.writerows(rows)
