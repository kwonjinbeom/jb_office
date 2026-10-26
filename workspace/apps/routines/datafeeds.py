"""공공 데이터 받아 쌓기 (2026-10-26 사용자: 블로그마다 고정 코너 + 공공 API 로 쌓는 표).

웹 검색이 자주 실패해 기획자가 최신 일정을 못 잡았다 (10-23~26 기획표) → 공공 API 값을 표로 받아 두고 글쓰기가 먼저 본다.
PC 에서 글쓰기 루틴 메인이 기획 전에 돌린다: `manage.py collect_data` (일일루틴/프롬프트/writing.md '데이터 폴더').

키는 workspace/.env (git 에 올라가지 않는다). 키가 없는 출처는 건너뛰고 그렇게 알린다. 한 곳이 실패해도 나머지는 계속.
  DATA_GO_KR_KEY  공공데이터포털 일반 인증키 (Decoding) — 관광공사 국문 관광정보(KorService2) 축제 · 청약홈 분양정보 (각각 활용신청)
  KOBIS_KEY       영화진흥위원회 오픈API 키 (주간 박스오피스)
  DART_KEY        OpenDART 인증키 (지분증권 증권신고서 = 공모주 새 종목 신호)
  FRED_KEY        FRED API 키 (나스닥·S&P500 종가)

쓰는 곳: 콘텐츠/블로그_카페/데이터/<이름>.csv (UTF-8, 첫 줄 머리). 같은 열쇠(첫 칸)는 새 값으로 바꾸고, 기간이 지난 줄은 지운다.
작가가 쌓는 표(시황노트.csv · 공모주.csv)는 머리만 만들어 두고 손대지 않는다. 형식은 그 폴더의 README.md.
"""
import csv
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

from django.conf import settings

TIMEOUT = 15
UA = "Mozilla/5.0 (JB Office data)"
LONG_EVENT = 92  # 축제.csv 에 넣는 행사의 최대 기간(일). 2026-10-26 첫 실행에 2022~2026 상설 전시가 섞였다


def data_dir() -> Path:
    return Path(getattr(settings, "BLOG_DATA_DIR", settings.REPO_ROOT / "콘텐츠" / "블로그_카페" / "데이터"))


def _key(name):
    """키. 공공데이터포털의 인코딩 키(%가 들어간 것)를 넣어도 되게 한 번 푼다 — 주소에 넣을 때 다시 인코딩한다 (2026-10-26)."""
    return urllib.parse.unquote(os.environ.get(name, "").strip())


def _get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return json.loads(r.read().decode("utf-8"))


def _ymd(d):
    return d.strftime("%Y%m%d")


def _dash(raw):
    """20261026 · 2026-10-26 → 2026-10-26 (빈 값은 빈 값)."""
    raw = (raw or "").strip()
    if len(raw) == 8 and raw.isdigit():
        return f"{raw[:4]}-{raw[4:6]}-{raw[6:]}"
    return raw[:10]


@dataclass
class Table:
    name: str  # 파일 이름 (확장자 없이)
    head: list  # 첫 칸이 열쇠

    @property
    def path(self) -> Path:
        return data_dir() / f"{self.name}.csv"

    def read(self):
        if not self.path.is_file():
            return {}
        with self.path.open(encoding="utf-8", newline="") as f:
            return {row[self.head[0]]: row for row in csv.DictReader(f) if row.get(self.head[0])}

    def write(self, rows, order):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=self.head, extrasaction="ignore", lineterminator="\n")
            w.writeheader()
            for row in sorted(rows.values(), key=order):
                w.writerow({k: row.get(k, "") for k in self.head})

    def merge(self, new_rows, keep=lambda row: True, order=None):
        """새 줄을 열쇠로 합치고 keep 이 False 인 줄을 지운다. (전체 줄 수, 새로 생긴 줄 수)"""
        rows = self.read()
        added = sum(1 for r in new_rows if r[self.head[0]] not in rows)
        for r in new_rows:
            rows[r[self.head[0]]] = r
        rows = {k: r for k, r in rows.items() if keep(r)}
        self.write(rows, order or (lambda r: r[self.head[0]]))
        return len(rows), added


FESTIVAL = Table("축제", ["열쇠", "제목", "시작", "끝", "지역", "주소", "경도", "위도", "전화", "받은 날"])
APT = Table("분양", ["공고번호", "주택", "지역", "주소", "모집공고일", "접수 시작", "접수 끝", "당첨 발표", "세대수", "주소 링크", "받은 날"])
BOXOFFICE = Table("박스오피스", ["열쇠", "주간", "순위", "영화", "개봉일", "주간 관객", "누적 관객", "순위 변동", "새로 진입", "받은 날"])
DART = Table("증권신고서", ["접수번호", "접수일", "회사", "보고서", "시장", "원문"])
US_INDEX = Table("미국지수", ["날짜", "나스닥", "S&P500"])
# 작가가 쌓는 표 — 머리만 (형식은 README.md)
MARKET_NOTE = Table("시황노트", ["no", "날짜", "코스피", "코스피 등락률", "코스닥", "코스닥 등락률", "나스닥 날짜", "나스닥", "나스닥 등락률",
                              "S&P500", "S&P500 등락률", "원달러", "외국인 순매수(억)", "메모", "글"])
IPO = Table("공모주", ["종목", "시장", "희망 밴드", "확정 공모가", "수요예측일", "기관 경쟁률", "의무보유확약(%)", "청약일", "청약 경쟁률",
                    "환불일", "상장일", "시초가", "첫날 종가", "확정가 대비(%)", "출처", "고친 날"])
WRITER_TABLES = (MARKET_NOTE, IPO)


def festivals(today):
    """관광공사 TourAPI 국문(KorService2) 축제: 오늘부터 45일 안에 열리거나 열리고 있는 것."""
    key = _key("DATA_GO_KR_KEY")
    if not key:
        return "키 없음 (DATA_GO_KR_KEY)"
    start, until = today - timedelta(days=60), today + timedelta(days=45)
    rows, page = [], 1
    while page <= 10:
        q = urllib.parse.urlencode({"serviceKey": key, "MobileOS": "ETC", "MobileApp": "JBOffice", "_type": "json",
                                    "numOfRows": 200, "pageNo": page, "arrange": "A", "eventStartDate": _ymd(start)})
        body = _get_json(f"https://apis.data.go.kr/B551011/KorService2/searchFestival2?{q}")["response"]["body"]
        items = body.get("items") or {}
        items = items.get("item", []) if isinstance(items, dict) else []
        if isinstance(items, dict):
            items = [items]
        for it in items:
            s, e = _dash(it.get("eventstartdate")), _dash(it.get("eventenddate"))
            if not s or e < today.isoformat() or s > until.isoformat():
                continue
            if e and (date.fromisoformat(e) - date.fromisoformat(s)).days > LONG_EVENT:  # 상설 전시·1년 내내 하는 행사는 축제가 아니다
                continue
            addr = " ".join(x for x in (it.get("addr1", ""), it.get("addr2", "")) if x).strip()
            rows.append({"열쇠": str(it.get("contentid", "")), "제목": it.get("title", ""), "시작": s, "끝": e,
                         "지역": addr.split(" ")[0] if addr else "", "주소": addr, "경도": it.get("mapx", ""), "위도": it.get("mapy", ""),
                         "전화": it.get("tel", ""), "받은 날": today.isoformat()})
        total = int(body.get("totalCount") or 0)
        if page * 200 >= total:
            break
        page += 1
    n, added = FESTIVAL.merge([r for r in rows if r["열쇠"]], keep=lambda r: r["끝"] >= (today - timedelta(days=7)).isoformat(),
                              order=lambda r: (r["시작"], r["제목"]))
    return f"{n}곳 (새 {added})"


def apartments(today):
    """청약홈 APT 분양정보: 최근 30일 모집공고. 접수 끝난 지 30일 지난 줄은 지운다."""
    key = _key("DATA_GO_KR_KEY")
    if not key:
        return "키 없음 (DATA_GO_KR_KEY)"
    q = urllib.parse.urlencode({"page": 1, "perPage": 200, "serviceKey": key,
                                "cond[RCRIT_PBLANC_DE::GTE]": (today - timedelta(days=30)).isoformat()})
    data = _get_json(f"https://api.odcloud.kr/api/ApplyhomeInfoDetailSvc/v1/getAPTLttotPblancDetail?{q}").get("data", [])
    rows = [{"공고번호": str(it.get("PBLANC_NO", "")), "주택": it.get("HOUSE_NM", ""), "지역": it.get("SUBSCRPT_AREA_CODE_NM", ""),
             "주소": it.get("HSSPLY_ADRES", ""), "모집공고일": _dash(it.get("RCRIT_PBLANC_DE")), "접수 시작": _dash(it.get("RCEPT_BGNDE")),
             "접수 끝": _dash(it.get("RCEPT_ENDDE")), "당첨 발표": _dash(it.get("PRZWNER_PRESNATN_DE")),
             "세대수": it.get("TOT_SUPLY_HSHLDCO", ""), "주소 링크": it.get("PBLANC_URL", ""), "받은 날": today.isoformat()} for it in data]
    cut = (today - timedelta(days=30)).isoformat()
    n, added = APT.merge([r for r in rows if r["공고번호"]], keep=lambda r: (r["접수 끝"] or r["모집공고일"]) >= cut,
                         order=lambda r: (r["접수 시작"], r["주택"]))
    return f"{n}건 (새 {added})"


def boxoffice(today):
    """KOBIS 주간(월~일) 박스오피스: 지난주. 12주치만 남긴다."""
    key = _key("KOBIS_KEY")
    if not key:
        return "키 없음 (KOBIS_KEY)"
    sunday = today - timedelta(days=today.weekday() + 1)
    q = urllib.parse.urlencode({"key": key, "targetDt": _ymd(sunday), "weekGb": "0"})
    res = _get_json(f"https://www.kobis.or.kr/kobisopenapi/webservice/rest/boxoffice/searchWeeklyBoxOfficeList.json?{q}")["boxOfficeResult"]
    week = res.get("showRange", "")
    rows = [{"열쇠": f"{week}#{int(it.get('rank', 0)):02d}", "주간": week, "순위": it.get("rank", ""), "영화": it.get("movieNm", ""),
             "개봉일": it.get("openDt", ""), "주간 관객": it.get("audiCnt", ""), "누적 관객": it.get("audiAcc", ""),
             "순위 변동": it.get("rankInten", ""), "새로 진입": "새" if it.get("rankOldAndNew") == "NEW" else "",
             "받은 날": today.isoformat()} for it in res.get("weeklyBoxOfficeList", [])]
    cut = _ymd(today - timedelta(weeks=12))
    n, added = BOXOFFICE.merge(rows, keep=lambda r: r["주간"][:8] >= cut, order=lambda r: (r["주간"], int(r["순위"] or 0)))
    return f"{week} {len(rows)}편 (전체 {n}줄)"


def dart(today):
    """OpenDART 증권신고서(지분증권, C001): 최근 30일. 180일치만 남긴다."""
    key = _key("DART_KEY")
    if not key:
        return "키 없음 (DART_KEY)"
    market = {"Y": "유가", "K": "코스닥", "N": "코넥스", "E": "기타"}
    rows, page = [], 1
    while page <= 10:  # 발행공시(C) 전체가 와서 (2026-10-26 첫 실행: 채권·실적보고서가 대부분) 지분증권 증권신고서만 남긴다
        q = urllib.parse.urlencode({"crtfc_key": key, "bgn_de": _ymd(today - timedelta(days=30)), "end_de": _ymd(today),
                                    "pblntf_ty": "C", "pblntf_detail_ty": "C001", "page_no": page, "page_count": 100})
        res = _get_json(f"https://opendart.fss.or.kr/api/list.json?{q}")
        if res.get("status") not in ("000", "013"):  # 013 = 조회된 데이터 없음
            raise RuntimeError(f"DART {res.get('status')} {res.get('message', '')}")
        rows += [{"접수번호": it.get("rcept_no", ""), "접수일": _dash(it.get("rcept_dt")), "회사": it.get("corp_name", ""),
                  "보고서": " ".join(it.get("report_nm", "").split()), "시장": market.get(it.get("corp_cls", ""), ""),
                  "원문": f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={it.get('rcept_no', '')}"} for it in res.get("list", [])]
        if page >= int(res.get("total_page") or 1):
            break
        page += 1
    cut = (today - timedelta(days=180)).isoformat()
    n, added = DART.merge([r for r in rows if r["접수번호"] and "지분증권" in r["보고서"]],
                          keep=lambda r: r["접수일"] >= cut and "지분증권" in r["보고서"], order=lambda r: (r["접수일"], r["접수번호"]))
    return f"{n}건 (새 {added})"


def us_index(today):
    """FRED 나스닥 종합(NASDAQCOM) · S&P500(SP500) 종가: 최근 400일."""
    key = _key("FRED_KEY")
    if not key:
        return "키 없음 (FRED_KEY)"
    start = (today - timedelta(days=400)).isoformat()
    rows = {}
    for series, col in (("NASDAQCOM", "나스닥"), ("SP500", "S&P500")):
        q = urllib.parse.urlencode({"series_id": series, "api_key": key, "file_type": "json", "observation_start": start})
        for ob in _get_json(f"https://api.stlouisfed.org/fred/series/observations?{q}").get("observations", []):
            if ob.get("value", ".") != ".":
                rows.setdefault(ob["date"], {"날짜": ob["date"]})[col] = ob["value"]
    n, _ = US_INDEX.merge(list(rows.values()), keep=lambda r: r["날짜"] >= start)
    last = max(rows) if rows else "-"
    return f"{n}일 (마지막 {last})"


SOURCES = [("축제", festivals), ("분양", apartments), ("박스오피스", boxoffice), ("증권신고서", dart), ("미국지수", us_index)]


def ensure_writer_tables():
    """작가가 쌓는 표가 없으면 머리만 만든다 (있으면 손대지 않는다)."""
    for t in WRITER_TABLES:
        if not t.path.is_file():
            t.write({}, order=lambda r: r)


def collect(today=None, only=None):
    """모든 출처를 차례로. [(이름, 결과 한 줄)]"""
    today = today or date.today()
    ensure_writer_tables()
    out = []
    for name, fn in SOURCES:
        if only and name not in only:
            continue
        try:
            out.append((name, fn(today)))
        except (urllib.error.URLError, OSError, ValueError, KeyError, TypeError, RuntimeError) as e:
            out.append((name, f"실패 ({type(e).__name__}: {str(e)[:80]})"))
    return out
