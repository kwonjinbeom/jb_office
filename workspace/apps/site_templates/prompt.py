"""변환 요청문: 사이트 템플릿 + 카테고리 컨셉 + 플랫폼 포맷 + 원문을 한 덩어리로.

- build: 글 하나의 요청문 (변환 화면의 '요청문' 복사, requests.json).
- launcher: 글 관리의 '변환'·'변환 가능 글 전체 변환'·'재변환'이 PC 터미널의 claude 에게 주는 안내문 (여러 편을 차례로 변환하고
  변환본을 서버의 저장 주소로 curl 로 보낸다. apps/routines/local_run.py 의 convert 실행).
"""
from django.urls import reverse
from django.utils import timezone

from apps.blog_rules.models import Blog

from . import looks, paste
from .models import PlatformFormat, SiteTemplate

LAUNCH_HEAD = "# 사이트 변환"  # local_run 이 이걸로 변환 안내문인지 본다

# 변환 때 사실 점검 (2026-10-20 사용자: 변환할 때 숫자·날짜·일정을 출처에서 다시 확인하고, 틀린 건 고치고, 무엇을 왜 고쳤는지
# 출처와 함께 변환 화면에 남긴다). 기록은 Placement.converted_check, 꼴은 paste.OUTPUT 의 '점검 기록'.
FACT_CHECK = """## 사실 점검 (변환할 때 꼭)
- 원문의 숫자·날짜·일정·기준값(지수·금리·금액·조건·시간)을 하나씩 출처에서 다시 확인한다 (웹 검색·브라우저). 공식 출처(기관·거래소·회사 발표)를 먼저, 없으면 믿을 만한 보도.
- 틀린 것은 변환본에서 고친다. 확인되지 않거나 아직 안 나온 일정은 '미정'으로 둔다. 추측으로 채우지 않는다.
- 맞는 것은 그대로 둔다. 원문에 없는 숫자·주장을 새로 더하지 않는다.
- 무엇을 왜 고쳤는지 출처 주소와 함께 '점검 기록'으로 남긴다 (아래 '돌려줄 것')."""


# 변환의 기준 (2026-10-21 사용자: 변환본이 원문보다 훨씬 못하다 — 말·표·글씨 모두 원문이 낫다. 사이트 템플릿·다듬기 규칙이
# 원문을 다시 짜면서 지저분하게 만들었다). 변환은 원문을 살리고, 플랫폼·사실·사진처럼 꼭 필요한 것만 바꾼다.
KEEP = """## 변환 원칙 (원문이 기준)
- 원문의 문장·말투·소제목·순서·표(칸까지)·이모지를 그대로 옮긴다. 다시 쓰거나 줄이거나, 표를 문장으로 풀거나, 원문에 없는 소제목·문장·요약을 더하지 않는다.
- 바꾸는 것은 이것뿐: 위 '붙여넣기 포맷'이 못 받는 것, 아래 '사실 점검'에서 틀린 값, 사진·그림(자리가 없어도 아래 '사진·그림' 기준대로 더한다). 사이트 템플릿·카테고리 컨셉은 원문이 크게 어긋날 때 그 부분만 맞춘다.
- 단 카테고리 컨셉에 '글 모양'이 있으면 그것은 원문에 없어도 변환이 채우고 맞춘다 (2026-10-23 사용자): 정보 카드(::: 장소|맛집|작품 | 이름), 갈 곳마다 사진·지도 링크(어느 지도인지는 사이트 템플릿·카테고리 컨셉대로), 포스터, 스펙 비교표, 빼라는 단락 빼기, 마무리 서술. 필요한 사실은 조사해 채우고 출처를 점검 기록에 남긴다.
- 정보성 글은 맨 위를 인용(>) 하나로 시작한다: 원문 첫머리의 결론 문장을 그대로 옮기고, '결론부터 말하면' 같은 이름표와 굵게만 뗀다. 원문이 이미 > 로 시작하면 그대로. 소개·감상 글은 넣지 않는다. 카테고리 컨셉이 첫머리를 따로 정하면 그것대로 (예: 시황 노트는 말 거는 한두 줄).
- [사진]·📷·[그림] 자리 줄은 변환본에 남기지 않는다 — 채우거나 지운다 (아래 '사진·그림'). 자리를 남기면 사람 손이 한 번 더 간다 (2026-10-21 사용자).
- 원고 작성용 메모 주석(`<!-- 제휴가 있으면 … -->` 같은 것)은 뺀다. 링크 자리(`[예약 링크 자리 …]`)는 남기지 않는다 — 실제 예약·예매·공식 페이지 주소를 찾아 걸고, 걸 곳이 없으면 지운다 (2026-10-23 사용자: 링크를 할 거면 끝까지 건다)."""

# 변환 때 사진 찾아 넣기 (2026-10-20 사용자: 사진은 변환할 때 찾아 넣는다. 2026-10-21: 못 찾으면 자리를 두지 말고 지운다).
# 저작권 때문에 상업적 사용이 무료인 사진 사이트만. 워드프레스도 넣는다 (2026-10-26 사용자: 외국인용 여행 글은 사진을 쭉 —
# 블록 에디터에 붙이면 주소 그대로 이미지 블록이 된다). 네이버도 서식 그대로 붙이면 사진 주소가 사진으로 옮겨진다 (2026-10-20 확인).
# 가공이미지 = 인터넷 사진이 아니라 직접 만든 그림 (2026-10-21 사용자: 필요한 곳에만). 그림은 공개 저장소 주소로 붙인다.
PHOTO_PLATFORMS = {"tistory", "blogger", "naver", "wordpress"}

# 블로거 라벨 (2026-10-22 사용자: 태그를 그대로 붙였더니 라벨이 태그급으로 많아졌다 → 5개쯤). 블로거는 라벨이 카테고리 겸 태그다.
BLOGGER_LABELS = 5
BLOGGER_TAGS = f"""## 블로거 라벨 (돌려줄 '태그 한 줄')
- 블로거는 라벨이 카테고리 겸 태그다. 라벨은 {BLOGGER_LABELS}개 안팎, 많아도 {BLOGGER_LABELS}개.
- 첫째는 넣을 카테고리 이름 그대로 (라벨 메뉴로 쓴다). 나머지는 이 글의 핵심 검색어 4개.
- 띄어쓰기 없이 짧게 (`시황노트`, `코스피`). 날짜·연도만 있는 라벨, 글마다 바뀌는 긴 문구는 쓰지 않는다."""
FIGURE_DIR = "콘텐츠/블로그_카페/변환그림"
FIGURE_URL = "https://raw.githubusercontent.com/kwonjinbeom/jb_office/main/"
PHOTOS = f"""## 사진·그림 (변환이 끝까지 채운다 · 원문에 자리가 없어도 판단한다)
- 원문에 자리가 없어도 글마다 두 가지를 판단한다 (2026-10-22 사용자: 자리가 없다고 사진·그림을 하나도 안 넣었다).
  ① 사진: 주제와 맞는 사진이 있으면 1장 넣는다 (맨 위 인용 다음, 또는 그 사진이 설명하는 단락 옆). 표·숫자 위주 정보 글도 주제의 장면(노트북 작업, 책상 위 서류, 거리 풍경 …)이면 된다. 억지로 맞추지는 않는다.
  ② 가공이미지: 핵심 숫자 하나·기간과 일정·순서·차이처럼 그림이 글·표보다 빨리 읽히는 곳이 있으면 필요한 만큼 만든다 (카테고리 컨셉이 장수를 정하면 그것대로, 아래 만드는 법). 표를 그대로 옮긴 그림, 사진과 같은 내용의 그림은 만들지 않는다.
  넣지 않았으면 점검 기록에 이유를 한 줄 남긴다 (`- 사진 안 넣음: …`, `- 그림 안 넣음: …`).
- 원문의 사진 자리마다 맞는 무료 사진을 찾아 넣는다. 맞는 사진이 없으면 그 줄을 지운다 (없던 것처럼, 앞뒤 문장도 자연스럽게).
- 사진 찾는 곳 — 갈 곳·산·절처럼 장소가 주인공이면 그 장소가 실제로 찍힌 사진이 먼저 (작가·라이선스 표기):
  - 국내 장소: 한국관광콘텐츠랩 고품질사진 (옛 포토코리아, 공공누리 제1유형) — 국내 이름난 산·절·관광지·축제는 거의 다 있다.
    `curl -s -X POST https://api.visitkorea.or.kr/hub/getTourPhotoInfo.do -H "Content-Type: application/json;charset=UTF-8" --data-binary @q.json`
    (q.json: `{{"type":"photo","lang":"KOR","cat1":[],"cat2":[],"cat3":[],"photo1":[],"photo2":[],"awardYear":[],"areaCd":[],"sigunguCd":[],"nuri":[],"title":"<장소 이름>","searchStart":0,"searchCnt":100,"pageNo":1,"pageCnt":1,"mainYn":"N","langDiv":"KOR","arrange":"NEW"}}`, UTF-8 파일로)
    → `cpyrhtDivCd` 가 `Type1` 인 것만, `filmDay`·`photoTag` 로 계절·지점이 맞는 것을 골라 `depotOrgImgUrl`(원본, 워터마크 없음)을 받아 너비 620 으로 줄여 올린다.
    캡션 `*사진: <koCmanNm> · 한국관광공사 (공공누리 제1유형)*`. 미리보기 주소(tong.visitkorea.or.kr …image2)는 워터마크가 있어 쓰지 않는다.
  - 해외 장소: 위키미디어 공용 (그 장소 이름 카테고리, CC0·CC BY·CC BY-SA) → Unsplash · Pexels · Pixabay.
  - 장소가 아닌 장면 (노트북 작업, 책상 위 서류 …): Unsplash · Pexels · Pixabay (상업적 사용 무료).
  - 구글 이미지·핀터레스트·뉴스·다른 블로그 사진은 쓰지 않는다.
- 카테고리 컨셉이 사진 장수를 정하면 (산과 캠핑 2~4장, 여행 Day 마다 …) 그 장수가 바닥이다. 위 찾는 곳을 모두 찾아보기 전에는 사진 자리를 지우거나
  '사진 안 넣음'으로 넘기지 않는다. 못 찾았으면 찾아본 곳과 검색어를 점검 기록에 적는다 (2026-10-27 사용자: 선운산 글에 산 사진이 하나도 없었다 — 원고가 말한 포토코리아를 찾지 않았다).
  컨셉이 '그림·사진 N장'처럼 그림도 받으면, 맞는 사진이 없을 때 그 글의 숫자로 가공이미지를 그려 채운다 (시황 노트: 수급 막대 · 장중 흐름 · 주인공 종목 —
  2026-10-27 사용자: 코스피 시황 노트에 지수 카드 말고 그림이 없었다).
- 크기 (2026-10-23 사용자: 너무 크다): 사진은 모두 너비 620 · 가운데. Unsplash·Pexels·Pixabay 는 이미지 파일 주소(images.unsplash.com · images.pexels.com · cdn.pixabay.com)를 너비 w=620 으로, 위키미디어·공공누리 사진은 너비 620 으로 줄여 아래 가공이미지와 같은 폴더·방법으로 올린다. 영화·OTT 포스터는 공식 포스터를 너비 300 으로 줄여 같은 폴더에 (`*포스터: 넷플릭스*`).
- `![설명](주소)` 한 줄로, 다음 줄에 `*사진: 작가 이름 · Pexels*`. `<div>`·`<p>`·`<center>` 로 감싸지 않는다 — 가운데 정렬은 서버가 하고, 감싸면 그림 대신 주소가 글자로 보인다 (2026-10-27). 상표·실존 인물 얼굴이 중심인 사진은 피한다 (공식 포스터·제품 사진은 예외).
- 원문의 그림 자리는 가공이미지(직접 그린 그림)를 만들어 넣거나 지운다.
  - 모양: 흰 바탕, Pretendard, 짙은 회색 글자, 포인트 컬러 한 가지, 장식 없이. 그림 속 숫자는 사실 점검을 마친 숫자.
  - 만드는 법: HTML 하나로 그리고 (Pretendard `https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css`) `chrome.exe --headless=new --hide-scrollbars --window-size=1260,1400 --virtual-time-budget=6000 --screenshot=<png> file:///<html>` → PIL 로 왼쪽 1200px·내용 높이만 자른다.
  - `{FIGURE_DIR}/<글 번호>/<이름>.png` 로 저장해 그 폴더만 git add · commit · push (main). 주소는 `{FIGURE_URL}<경로를 퍼센트 인코딩>` — curl 로 200 을 확인하고 `![설명](주소)` 한 줄로.
- 점검 기록에 `- 사진: 설명 · 사진 페이지 주소` · `- 그림: 파일 이름 · 무엇을 보여 주나` · `- 지움: 찾지 못한 자리` 로 남긴다."""

# 여행 글 맨 위 위치 지도 (2026-10-27 사용자: "나는 사실 어딘지도 몰라 너가 쓰는 지역들이"). 카테고리 컨셉에 '위치 지도'가
# 있으면 붙는다 (밤밤 › 해외여행 · 워드프레스 › World Travel 0037, black_lukey › 지역 놀거리 0038, 워드프레스 › Korea Travel 0039). 대표 사진에서는 빠진다 (views._hero).
LOCATOR_NAME = "위치지도.png"
LOCATOR = f"""## 위치 지도 (원문에 자리가 없어도 꼭)
- 맨 위 인용 바로 다음에 한 장 — 인용 아래 대표 사진이 있으면 그 사진 다음. 다른 사진·그림과 별개로 센다.
- 그리는 법 (Natural Earth 지도, 사이트마다 모양이 다르다):
  `python {FIGURE_DIR}/위치지도.py <밤밤|워드프레스|black_lukey> <나라 ISO3 | 시도 코드> <도시> <위도> <경도> {FIGURE_DIR}/<글 번호>/{LOCATOR_NAME} --near "<이웃 도시:위도:경도>,…"`
  - 해외는 나라 ISO3 (AUT · HKG · ITA), 국내(black_lukey · 워드프레스 Korea Travel)는 시도 코드 (KR-11 서울 · KR-26 부산 · KR-48 경남 · KR-42 강원 · KR-47 경북 · KR-49 제주 …).
  - 도시 이름은 글의 말로 (밤밤·black_lukey 한국어, 워드프레스 영어). `--near` 는 독자가 알 만한 이웃 도시 3~5곳 (같은 말로).
  - 나라가 작아 가까운 지도가 너무 좁으면 `--span 3` 처럼 가로 폭(경도)을 넓힌다 (홍콩·싱가포르·마카오).
- 다른 가공이미지처럼 그 폴더만 커밋·push 하고 `![<도시> 위치 지도](주소)` 한 줄로 (밤밤 '비엔나 위치 지도', black_lukey '통영 위치 지도', 워드프레스 'Map: where Rome is'). 캡션 줄은 달지 않는다 (지도 안에 출처가 있다).
- 점검 기록에 `- 그림: {LOCATOR_NAME} · <도시> 위치` 한 줄."""


def template_for(blog):
    tpl, _ = SiteTemplate.objects.get_or_create(blog=blog)
    return tpl


def format_for(platform):
    fmt, _ = PlatformFormat.objects.get_or_create(platform=platform)
    return fmt


def build(placement):
    cat = placement.site_category
    blog = cat.blog
    tpl, fmt, post = template_for(blog), format_for(blog.platform), placement.post
    parts = [
        f"아래 원문을 '{blog.name}'({blog.get_platform_display()})에 올릴 수 있게 변환해 주세요. 원문이 기준입니다 — "
        "글은 그대로 살리고 아래 '변환 원칙'에 적힌 것만 바꿉니다.",
        f"## 사이트\n- 이름: {blog.name}\n- 플랫폼: {blog.get_platform_display()}\n- 컨셉: {blog.content or '-'}\n- 넣을 카테고리: {cat}",
        _category_part(cat),
        _template_part(tpl),
        f"## {blog.get_platform_display()} 붙여넣기 포맷\n{fmt.guide}" if fmt.guide.strip() else "",
        KEEP,
        FACT_CHECK,
    ]
    if blog.platform in PHOTO_PLATFORMS:
        parts.append(PHOTOS)
        if "위치 지도" in _category_part(cat):
            parts.append(LOCATOR)
    if (cat.look or (cat.parent.look if cat.parent_id else "")) == "yudi":
        parts.append(looks.PROMPT)
    if blog.platform == "blogger":
        parts.append(BLOGGER_TAGS)
    if blog.platform == "wordpress":  # 워드프레스 글 모양 (2026-10-26)
        from . import wp_looks
        parts.append(wp_looks.PROMPT)
    if placement.convert_note:
        parts.append(f"## 이 글만\n{placement.convert_note}")
    parts.append(f"## 원문\n### 제목\n{post.title}\n### 본문\n{post.body}")
    parts.append(paste.OUTPUT)
    return "\n\n".join(p for p in parts if p)


def _template_part(tpl):
    """사이트 템플릿 중 채운 칸만 (빈 칸은 '-' 로 늘어놓지 않는다)."""
    lines = [f"### {label}\n{value.strip()}" for label, value in
             (("말투", tpl.tone), ("구성", tpl.structure), ("꼭 지킬 것", tpl.rules)) if value.strip()]
    return "## 사이트 템플릿\n" + "\n".join(lines) if lines else ""


def _category_part(cat):
    """카테고리 컨셉 (하위 카테고리면 위 카테고리 것부터). 없으면 빈 값."""
    lines = [f"- {c.name}: {c.concept.strip()}" for c in (cat.parent, cat) if c is not None and c.concept.strip()]
    return "## 카테고리 컨셉\n" + "\n".join(lines) if lines else ""


def launcher(request, placements, token, redo=""):
    """PC 터미널 claude 에게 줄 안내문: 글마다 요청문대로 변환 → 본문 파일 → 서버 저장 주소로 curl.
    redo: 재변환 코멘트 (2026-10-22 사용자, 글 관리에서 한 건씩). 지난 변환본을 코멘트대로 고친다."""
    day = timezone.localdate()
    head = [
        f"{LAUNCH_HEAD} · {day.isoformat()} · {len(placements)}편",
        "아래 글을 각 사이트·카테고리에 맞게 변환하고 변환본을 서버로 보낸다. 사용자에게 묻지 않고 끝까지 한다. "
        f"git 커밋·push 는 가공이미지 폴더({FIGURE_DIR})만 한다 (변환본은 서버 DB 에만 들어간다).",
        "## 글마다 하는 일\n"
        "1. 그 글의 요청문대로 변환한다. 숫자·날짜·일정은 요청문의 '사실 점검'대로 출처에서 다시 확인하고 틀린 것만 고친다. 링크는 바꾸지 않는다.\n"
        "2. 본문만 `workspace/.routine/convert/<번호>.md`, 점검 기록은 `<번호>-check.md`, 제목 한 줄은 `<번호>-title.txt`, "
        "태그 한 줄은 `<번호>-tags.txt` 로 같은 폴더에 쓴다 (모두 UTF-8). 제목·태그를 명령줄에 직접 쓰지 않는다 — "
        "Windows 는 명령줄 글자를 cp949 로 바꿔 — 같은 글자가 ? 로 깨진다 (2026-10-26).\n"
        "3. 아래 '보내기' 명령을 그대로 실행한다. 응답이 `ok` 로 시작하면, 워드프레스 글은 이어서 '초안 올리기' 명령도 실행한다 "
        "(`건너뜀`·실패여도 변환은 끝난 것이니 한 줄로 말하고 넘어간다). 그다음 글.\n"
        "4. 실패하면 이유를 한 줄로 말하고 다음 글로 간다. 다 끝나면 보낸 편수와 고친 곳 수를 한 줄로 말한다.",
    ]
    if redo:
        head[0] = f"{LAUNCH_HEAD} (재변환) · {day.isoformat()} · {len(placements)}편"
        head.insert(2, "## 재변환 코멘트 (사용자)\n" + redo.strip() + "\n\n"
                    "이 코멘트를 먼저 따른다. 아래 '지난 변환본'이 있으면 처음부터 다시 쓰지 말고 그것을 코멘트대로 고친다. "
                    "코멘트가 말하지 않은 부분은 지난 변환본 그대로 둔다. 사실 점검 기록에 무엇을 고쳤는지 한 줄 더한다.")
    parts = ["\n\n".join(head)]
    for n, pl in enumerate(placements, start=1):
        url = request.build_absolute_uri(reverse("site_templates:api_save", args=[pl.pk])) + f"?token={token}"
        send = (f'curl -fsS -X POST "{url}" --data-urlencode "title@workspace/.routine/convert/{pl.pk}-title.txt" '
                f'--data-urlencode "tags@workspace/.routine/convert/{pl.pk}-tags.txt" '
                f'--data-urlencode "body@workspace/.routine/convert/{pl.pk}.md" '
                f'--data-urlencode "check@workspace/.routine/convert/{pl.pk}-check.md"')
        wp = ""
        if pl.site_category.blog.platform == Blog.Platform.WORDPRESS:  # 초안 올리기 (2026-10-26 사용자, site_templates.wp_rest)
            send += f' --data-urlencode "slug@workspace/.routine/convert/{pl.pk}-slug.txt"'
            wp_url = request.build_absolute_uri(reverse("site_templates:api_wp", args=[pl.pk])) + f"?token={token}"
            wp = (f"슬러그 한 줄(영문 소문자-하이픈 3~6단어)을 `workspace/.routine/convert/{pl.pk}-slug.txt` 에 먼저 쓴다.\n\n"
                  f"초안 올리기 (보내기가 ok 인 뒤):\n```\nworkspace/.venv/Scripts/python.exe workspace/manage.py wp_draft \"{wp_url}\"\n```\n\n")
        part = (f"---\n\n## 글 {n} · 번호 {pl.pk} · {pl.site_category.blog.name} › {pl.site_category}\n\n"
                f"보내기:\n```\n{send}\n```\n\n{wp}{build(pl)}")
        if redo and pl.converted_body.strip():
            part += (f"\n\n## 지난 변환본 (재변환 코멘트대로 고친다)\n### 제목\n{pl.converted_title or '-'}\n"
                     f"### 태그\n{pl.converted_tags or '-'}\n### 본문\n{pl.converted_body}")
        elif pl.converted_body.strip() and pl.convert_note.strip():
            # 다시 변환 + '이 글만' (2026-10-23: 카테고리 글 모양을 바꾼 뒤 지난 변환본의 사진·사실은 살리고 모양만 새로)
            part += (f"\n\n## 지난 변환본 (사진·사실 점검은 살리고 위 '이 글만'대로 고친다)\n### 제목\n{pl.converted_title or '-'}\n"
                     f"### 태그\n{pl.converted_tags or '-'}\n### 본문\n{pl.converted_body}")
        parts.append(part)
    return "\n\n".join(parts)
