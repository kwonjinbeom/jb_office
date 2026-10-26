"""워드프레스 글 모양·컨셉 다듬기 (2026-10-26 사용자: 카테고리마다 맞는 컨셉·글 구조·CSS, 정보 위주지만 정성껏 · 길어도 된다).

근거: 카테고리마다 잘 쓴 글 10~14편 조사 (산과 캠핑 · 드라이브·자동차 · 영어 여행) — 상위 글이 공통으로 빠뜨린 것을 구조에 넣었다.
1. 사이트 카테고리 글 모양(look): 산과 캠핑 = wp_mountain · 드라이브·자동차 = wp_car · Korea Travel·World Travel = wp_travel.
2. 컨셉: 0030 에서 넣은 값 그대로일 때만 아래 구조로 바꾼다 (사용자가 고친 컨셉은 건드리지 않는다).
3. 워드프레스 붙여넣기 포맷: 마크다운 대신 '사용자 정의 HTML' 블록 (코드 편집기) — wp_looks.
4. 위쪽 바로가기에 jinbaam.com · 워드프레스 새 글.
지우는 데이터 없음.
"""
from importlib import import_module

from django.db import migrations

LOOKS = {"산과 캠핑": "wp_mountain", "드라이브·자동차": "wp_car", "Korea Travel": "wp_travel", "World Travel": "wp_travel"}

MOUNTAIN = "\n".join([
    "산 하나를 잡고 그 계절의 가장 좋은 모습으로 깊게 소개한다 (2026-10-26 사용자). 길어도 된다 — 대신 블록마다 정리해서.",
    "계절: 봄 벚꽃·진달래·철쭉 / 여름 신록·계곡·숲 그늘 / 가을 단풍·억새 / 겨울 상고대·눈꽃·해돋이. 2~4주 뒤 절정인 산이 먼저.",
    "초점은 그 산에 자연스러운 하나 — 등산형(정상 풍경이 이야기) · 나들이형(케이블카·곤돌라·둘레길·사찰) · 캠핑형(산 아래 야영장이 주인공). 초점이 아닌 블록은 줄이거나 뺀다.",
    "",
    "글 모양 (상위 글이 빠뜨리는 것 — 기관별 절정일 비교 · 탐방로 예약제·통제 · 하산 마감 · 화장실·물 · 대중교통 · 누적 오르막 — 을 꼭 채운다):",
    "1. 맨 위 인용(리드) 2~3문장: 지금 볼 것 + 핵심 숫자 1~2개 + 기준일.",
    "2. `::: 요약 | ○○산 한눈에` 카드 — 고정 순서: 🍂 지금 볼 것 · ⛰️ 높이·위치 · 🥾 추천 코스 · ⏱️ 거리·시간 · 📈 난이도 · 🎫 예약 · 🅿️ 주차 · 📅 기준일.",
    "3. `## 왜 지금 ○○산인가` — 계절 성격 + 절정 예측 표(기관 | 예측일 | 발표일). 기관끼리 다르면 둘 다.",
    "4. `## 코스 고르기` — 비교표: 코스 | 들머리 | 거리(왕복/편도 표시) | 시간 | 누적 오르막 | 난이도 | 이런 분께 (2~4줄).",
    "5. `## ○○ 코스 따라가기` — 지점 단계 목록 (① 들머리 (화장실) 0.0km → ② … 누적 거리·시간·특징 한 줄) + `::: 코스 | 코스 이름` 카드 "
    "(🥾 코스 · 📏 거리 · ⏱️ 시간 · ⛰️ 누적 오르막·최고점 · 📈 난이도 · 🚻 화장실·물 · 🕓 하산 마감 · 📍 들머리 지도) + 고도 그림 1장(가공이미지).",
    "6. (자연스러울 때만) `## 산 아래에서` — `::: 캠핑 | 야영장` (⛺ 운영·동절기 · 🏕️ 사이트(바닥·면 수) · 🔌 전기·온수 · 💳 요금 · 🎫 예약 방법·열리는 날 · 🐕 반려동물 · 🚗 산까지) "
    "또는 `::: 나들이 | 시설` (🚡 운행 시간 · 💳 요금 · 🎫 예약 · 🚶 내려서 걷는 거리 · 📅 쉬는 날).",
    "7. `## 가는 법` — 표: 수단 | 출발 | 걸리는 시간 | 요금 | 내리는 곳. 자가용은 주차장 이름·요금·만차 시각.",
    "8. `## 예약·통제·안전` — 탐방로 예약제·차량 통제·산불조심기간 · 입산 시간·하산 마감 · 일몰 시각 · 계절 준비물 3~5개 (체크 목록). 예약이 없으면 '예약 없음' 한 줄.",
    "9. (필요할 때) `## 자주 묻는 질문` 3~4개 — 실제로 묻는 말 그대로.",
    "10. 마무리 서술 2~3문장 + `참고:` 출처(기관·문서·확인일).",
    "- 숫자는 산림청·국립공원공단·지자체·고캠핑에서 확인하고 기준일. 확인 못 한 블로그 값은 쓰지 않는다.",
    "- 사진: 그 산이 그 계절에 실제로 찍힌 무료 사진 2~4장. 경험(\"올라 보니\")은 쓰지 않는다. 감상은 풍경에 대한 한 줄까지.",
])
CAR = "\n".join([
    "차 가진 사람들이 흥미로워하는 것 전부 (2026-10-26 사용자). 신차 출시 소식도 여기. 길어도 된다 — 표·체크 목록으로 정리.",
    "공통: 맨 위 인용(리드, 결론 2~3문장) → `::: 요약 | 한눈에` 카드 → 본문 → `참고:` 출처(기관·문서·날짜) → 기준일 줄('2026-10-26 기준, 바뀌면 고칩니다').",
    "글 종류를 돌린다 (상위 글이 빠뜨리는 것: 트림별 가격 차이 · 출고일 · 출처 있는 세율 · 수치 있는 체크리스트 · 드라이브의 주차·혼잡·통행료):",
    "A. 신차·연식 변경 — `::: 차 | 차명` (🚗 구분(완전·부분·연식 변경) · 📅 공개·계약·출고 · 💳 시작가~최고가 · ⚙️ 파워트레인 · ⛽ 복합연비 · 🆚 경쟁차) → 무엇이 바뀌었나(5줄 이하) → "
    "트림 가격표(트림 | 가솔린 | 하이브리드 | 구형 대비) → 기본이 된 사양(체크 목록) → 제원 비교표(구형 | 신형 | 차이) → 경쟁차 시작가 표 → 유리한 사람·불리한 사람 → 세제·출고 주의.",
    "B. 돈·규칙 (세금·기름값·통행료·검사·과태료·보험) — `::: 비용 | 무엇` (👥 대상 · 📅 기간·마감 · 💰 금액·비율 · 🏛️ 신청처 · 📄 근거 · 🔖 상태(확정·정부안·국회 심의)) → 날짜 표 → "
    "계산표(예: 배기량별 세액·공제액) → 신청 단계(번호, 화면 이름) → 자주 묻는 것 4~6개. 상태 표시와 숫자마다 기준일 필수.",
    "C. 기능·노하우 (경고등·겨울 배터리·타이어·전기차 충전) — `::: 점검 | 항목` (⚠️ 증상 · 🚦 위험도 · 🔧 바로 할 일 · 🗓️ 점검 주기 · 💰 비용 범위 · 📄 근거) → 왜 생기나(원리 3줄 + 도식) → "
    "체크리스트 표(항목 | 기준 수치 | 어디서 확인) → 상황별 대처(번호) → 하지 말 것 → 전기차·하이브리드는 다른 점.",
    "D. 드라이브 코스 ('길'이 주인공 — 산과 캠핑·Korea Travel 과 겹치지 않게) — `::: 장소 | 코스` (🛣️ 출발~도착 · 📏 거리 · ⏱️ 평일·주말 시간 · 🔢 IC·국도 · 💳 통행료(1종) · 🅿️ 주차 · 🕓 혼잡 시간 · ⛽ 주유·충전) → "
    "코스 그림(가공이미지) → 구간별(거리·볼 것·주의) → 막히는 시간 피하는 법 → 들를 곳 2~3 → 겨울·야간 주의.",
    "- 숫자는 제조사 가격표·뉴스룸, 오피넷, 한국도로공사, 위택스, 한국교통안전공단, 타이어·배터리 제조사 자료로 확인. 타 본 척(\"타 보니\") 금지 — 시승기는 '타 본 사람들은 …'으로 출처를 단다.",
    "- 사진: 제조사 보도사진(출처 표기) 또는 무료 사진. 그림: 원리 도식·코스 그림 가공이미지.",
])
TRAVEL_COMMON = [
    "공통 (상위 영어 글이 빠뜨리는 것: 시간이 적힌 일정 표 · 예산 표 · 2026년 바뀐 제도 · 공식 기준 요금 — 'Checked on 날짜'):",
    "- 제목: `{N} Days in {City} ({Mon} 2026): {약속 한 구절}`.",
    "- 맨 위 인용(리드) 2~3문장: 누구에게 맞는 글 · 핵심 동선 · 'Fares and hours checked on 26 Oct 2026'.",
    "- 장소 카드 `::: Place | Name (현지 표기)`: 📍 Address/Nearest station · 🕘 Hours · 🎟 Admission (checked) · 🚌 Getting there · ⏱ Time needed · ✅ Must / Nice / Skip.",
    "- 날짜 머리 `## Day 1 · {지역}` + 시간 표(Time | Stop | Time there | Move). 숙소는 `::: Stay` (동네 단위, 특정 호텔 칭찬 금지), 음식은 `::: Food` (이름 + 현지 표기 + 대략 가격).",
    "- `## Budget` 표(Item | Budget | Mid-range, 현지 통화 + USD 대략). FAQ 3~5개.",
    "- 끝에 `Sources:` 공식 링크 + 확인 날짜. 사진은 그 장소가 실제로 찍힌 무료 사진. 경험(\"we visited\")은 쓰지 않는다.",
]
KOREA = "\n".join([
    "외국인 관광객(영미권·일본·중국)에게 한국의 한 지역을 영어로 소개한다 (2026-10-26 사용자). 길어도 된다.",
    *TRAVEL_COMMON,
    "순서: 리드 → `## {City} at a Glance` (`::: Info | {City} at a glance` — 📍 Where · 🗓 Best time · ⏱ Days needed · 🚆 From Seoul / Busan / Incheon Airport · 💳 Pay · 🛂 Entry(K-ETA) · 🔤 Search names(한글)) → "
    "`## Before You Go (2026 Changes)` (바뀐 것만 5줄: 코레일+·예매 시작·네이버 여권 인증·K-ETA 면제 2026-12-31 등, 글마다 공식 확인) → `## Getting There` 표(From | Mode | Time | Fare (checked) | How foreigners book) + `::: Route` → "
    "`## Getting Around` → Day 1·Day 2 … → `## Where to Stay` → `## What to Eat` → `## Budget for N Days` → `## Practical Tips for Foreign Visitors` (결제·택스 리펀드·앱(Naver Map, Kakao T, Papago)·1330) → `## FAQ` → "
    "`## 日本語まとめ` · `## 中文简介` (각 4~5줄, 문장 말고 항목: どこ/おすすめ時期/流れ/入国/ひとこと · 地点/最佳时间/行程/入境/小贴士 — 중국어 입국 줄은 중국 대륙 여권 기준(비자)으로, 숫자·이름은 본문과 같게) → Sources.",
    "- 한국 공식 출처(VisitKorea·코레일·문화재청·지자체)로 요금·시간을 확인한다 — 영어 블로그끼리 틀린 값이 많다(무료인 곳을 유료로).",
    "- black_lukey 의 같은 지역 글을 번역하지 않는다 — 외국인이 막히는 것(교통·언어·결제·예약)으로 새로 짠다.",
])
ABROAD = "\n".join([
    "해외 한 도시의 N박 N일을 영어로 (2026-10-26 사용자: 밤밤 해외여행처럼). 길어도 된다.",
    *TRAVEL_COMMON,
    "순서: 리드 → `## Trip at a Glance` (`::: Info | {City} in N days` — 🗓 Best for · 🌡 Weather · 💱 Currency & cards · 🛂 Entry (US/UK/AU) · ✈️ From the airport · 💸 Daily budget) → `## What's New in 2026` (그 나라 제도 변화만) → "
    "`## Itinerary Overview` 표(Day | Area | Highlights | Pace) → Day 1·2·3 (Morning/Afternoon/Evening ### 소제목) → `## If You Have One More Day` (`::: Tour`) → `## Getting There & Around` (`::: Route`) → "
    "`## Where to Stay` → `## Budget` → `## Entry & Money Checklist` (비자·입국카드·카드/현금·환급, travel.state.gov · GOV.UK · Smartraveller 링크) → `## FAQ` → Sources.",
    "- 밤밤의 한국어 글을 번역하지 않는다. 같은 도시는 밤밤과 21일 안에 겹치지 않게.",
])
CONCEPTS = {"산과 캠핑": MOUNTAIN, "드라이브·자동차": CAR, "Korea Travel": KOREA, "World Travel": ABROAD}

FORMAT = "\n".join([
    "본문은 class 를 단 HTML 을 '사용자 정의 HTML' 블록 하나로 붙인다: 새 글 → 오른쪽 위 ⋮ → 코드 편집기 → 붙여넣기 → 코드 편집기 나가기.",
    "모양은 외모 › 사용자 정의하기 › 추가 CSS 에 한 번 넣은 글모양.css 가 입힌다 (콘텐츠/블로그_카페/워드프레스/글모양.css). 변환본에는 꾸밈 코드를 넣지 않는다.",
    "사진은 `![설명](주소)` 그대로 — 붙여 넣으면 사진이 된다 (설명이 대체 텍스트). 출처 줄은 사진 바로 아래 기울임 한 줄.",
    "제목은 60자 안쪽, 슬러그는 영문 짧게, 요약(발췌)에 소개 한두 문장.",
])
LINKS = [("jinbaam.com", "https://jinbaam.com/"), ("워드프레스 새 글", "https://jinbaam.com/wp-admin/post-new.php")]


def forward(apps, schema_editor):
    o30 = import_module("apps.blog_types.migrations.0030_wordpress_sites")
    SiteCategory = apps.get_model("blog_types", "SiteCategory")
    SiteLink = apps.get_model("blog_types", "SiteLink")
    PlatformFormat = apps.get_model("site_templates", "PlatformFormat")
    old = {"산과 캠핑": o30.MOUNTAIN, "드라이브·자동차": o30.CAR, "Korea Travel": o30.KOREA, "World Travel": o30.ABROAD}
    for cat in SiteCategory.objects.filter(blog__platform="wordpress", parent=None, name__in=list(CONCEPTS), deleted_at__isnull=True):
        fields = []
        if not cat.look:
            cat.look = LOOKS[cat.name]
            fields.append("look")
        if cat.concept.strip() in ("", old[cat.name].strip()):
            cat.concept = CONCEPTS[cat.name]
            fields.append("concept")
        if fields:
            cat.save(update_fields=fields)
    for fmt in PlatformFormat.objects.filter(platform="wordpress"):
        if "블록 에디터에 마크다운 그대로 붙인다" in fmt.guide or not fmt.guide.strip():
            fmt.guide = FORMAT
            fmt.save(update_fields=["guide"])
    last = SiteLink.objects.order_by("-order").first()
    order = (last.order + 1) if last else 0
    for name, url in LINKS:
        if not SiteLink.objects.filter(url=url).exists():
            SiteLink.objects.create(name=name, url=url, order=order)
            order += 1


class Migration(migrations.Migration):
    dependencies = [
        ("blog_types", "0031_site_category_wp_looks"),
        ("site_templates", "0010_naver_parking_address"),
    ]
    operations = [migrations.RunPython(forward, migrations.RunPython.noop)]
