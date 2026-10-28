"""애니 총정리 '글쓰기·변환' (2026-10-23 사용자): 원고 없는 담은 작품을 PC 터미널 claude 가 글쓰기부터 변환까지 한 번에.

일일루틴과 따로 돈다 (오래 걸리고 일체라서). 작품마다 새 터미널을 차례로 연다 (apps/routines/local_run 의 anime 실행).
처음부터 memorily › 애니 용으로 쓰는 글이라 변환본 = 원고: claude 가 원고를 main 에 올린 뒤 api_place 를 부르면
서버가 place_drafts.place 로 발행예정글 + 카테고리 매핑 + 변환 완료로 넣는다 (예전 migration 0014·0020 과 같은 일).
"""
from django.urls import reverse
from django.utils import timezone

from apps.blog_rules.models import Blog
from apps.blog_types.models import SiteCategory

HEAD = "# 애니 총정리"  # local_run 이 이걸로 이 안내문인지 본다
PART = "<!-- 애니 총정리 작품: {key} -->"  # local_run.ANIME_PART 와 같은 꼴 (작품마다 새 터미널)
ANIME = "콘텐츠/블로그_카페/memorily_티스토리/애니총정리"
CALC = "콘텐츠/블로그_카페/memorily_티스토리/애니환산기"
DRAFTS = "콘텐츠/블로그_카페/포스팅자동화/원고"


def concept():
    """memorily › 애니 카테고리 컨셉 (사이트별 템플릿에서 고친 대로). 없으면 빈 값."""
    blog = Blog.objects.filter(name="memorily").first()
    cat = blog and SiteCategory.objects.filter(blog=blog, name__startswith="애니").order_by("pk").first()
    return cat.concept.strip() if cat else ""


def part(request, anime, token, rule):
    url = request.build_absolute_uri(reverse("anime:api_place", args=[anime.pk])) + f"?token={token}"
    send = f'curl -fsS -X POST "{url}" --data-urlencode "folder=<원고 폴더 이름>" --data-urlencode "doc=<작품 md 이름>"'
    return f"""{PART.format(key=f"a{anime.pk}")}
## {anime.title} — 회차정리 글쓰기·변환

사용자에게 묻지 않고 끝까지 한다. 이 작품 하나만 한다.

### 먼저 읽기
- `{ANIME}/00_작업순서.md` (순서·규칙의 기준)
- 이미 쓴 원고 두 편: `{DRAFTS}/T111_히로아카환산기/원고.md` (한 판 · 기 표), `{DRAFTS}/T110_강철의연금술사환산기/원고.md` (두 판). 머리(사이트 · 커스텀 · 항목 표 · 확인한 사실)와 본문 표시까지 같은 꼴로 쓴다.
- `{CALC}/build.py` · `그림.py` · `환산기.js`

### 카테고리 컨셉 (memorily › 애니)
{rule or "(비어 있음 — 00_작업순서.md 를 따른다)"}

### 할 일
1. `git pull` 로 main 최신. 작품 키(영어 소문자, 예: mha)를 정한다.
2. 수요 조사: 구글 자동완성(`suggestqueries.google.com/complete/search?client=firefox&hl=ko&q=…`, 파이썬 urllib)으로 `<작품> 몇`·`몇화`·`몇기`·`만화`·`순서`·`극장판`·`명장면`·줄임말을 모은다.
3. 회차 데이터 `{CALC}/data/<키>.json`: 작품 fandom 위키 회차 문서와 Anime Filler List 를 대조 (다르면 위키). 회차 수 · 원작 화가 늘어나기만 하는지 · 마지막 원작 화를 점검한다. 연재 중이면 volEnd.
4. data 파일 `alias` 에 줄임말 · 흔한 오타를 넣고(작품 이름은 따로 안 넣어도 받는다) `python build.py` (`환산기데이터.json` 이 새로 나온다. 스킨은 다시 붙이지 않는다).
5. 가공이미지: `python 그림.py <키> "<작품 색>" "<막대 그림 아래 한 줄>"` 를 {CALC} 에서. 그림을 열어 글자가 넘치지 않는지 본다.
6. 장면 사진: 그 장면이 실제로 나오는 위키 그림을 620 폭 주소로, 열리는지(200) 확인한다. 명장면 5장 + 나머지는 표. 회차 제목 화면(타이틀 카드, 회차 문서의 `Episode_N.png` 가 그런 위키가 있다)은 쓰지 않는다 — 넣기 전에 브라우저로 열어 보고, 찾는 법은 00_작업순서.md '5. 사진' (2026-10-29 사용자: 블랙 클로버 명장면이 전부 제목 화면이었다).
7. 원고: `{DRAFTS}/T<다음 번호>_<짧은 이름>환산기/원고.md` (번호는 원고 폴더의 가장 큰 T 번호 + 1). 제목은 검색 질문형이되 **그 작품에만 있는 말로 묻는다** (2026-10-28 사용자: 작품 이름만 바꾸면 어느 작품에나 맞는 제목은 형식적이다). 2번 자동완성에서 그 작품만의 편·시리즈·사건 이름(무한성편 · 땅울림 · Z·카이·슈퍼·GT · 3기 · 천년혈전 · 완결편 · 산왕전 같은 것)을 골라 질문에 넣는다: `{anime.title} <그 말이 든 질문>? 화수 환산기·<그 작품에 맞는 것 1~2개 (보는 순서 · 극장판 순서 · 오리지널 회차 · 명장면 몇 화)>` — 좋은 예 (발행한 글) `귀멸의 칼날 무한성편은 만화 몇 권부터? 화수 환산기와 극장판까지 보는 순서` · `진격의 거인 총 몇 화, 몇 기까지? 화수 환산기·보는 순서·땅울림 몇 화` · `드래곤볼 보는 순서 Z·카이·슈퍼·GT, 애니 몇 화가 만화 몇 권? 화수 환산기`. 쓰지 않는 예 `슬램덩크 애니 몇 화까지 만화 몇 권? 화수 환산기·극장판 순서` (작품 이름만 바꾸면 어디에나 맞는다). 그 작품에 없는 것을 묻지 않고 (몇 기로 나뉘지 않은 작품에 '몇 기'), 제목이 묻는 것에 본문 소제목이 답한다. '회차정리 애니만화 환산기 명장면 등 모음' 같은 나열 제목도 쓰지 않는다. 본문은 `# 제목` 다음 한 문장 `<작품(한국 줄임말)> 애니 몇 화가 만화 몇 화·몇 권인지, 아래 환산기에 화수를 넣으면 바로 나와요.` 로 열고 '화수 환산기'로 간다 (검색 요약에 `[환산기: …]` 줄이 보이지 않게).
8. 작품 md: `{ANIME}/<다음 두 자리 번호>_<짧은 이름>.md` (05·06 과 같은 꼴, 상태 `원고 완료 (<날짜>) · 발행 전`).
9. 이 작품 파일(data · 환산기데이터.json · 사진 4장 · 원고 · 작품 md)만 `git add` 해 커밋 하나로 main 에 push 한다.
10. 서버에 넣기 (발행예정글 + memorily › 애니 매핑 + 변환 완료). <> 를 채워 실행한다:
```
{send}
```
   응답이 `ok` 로 시작하면 끝. `원고 없음` 이면 서버가 아직 push 를 받기 전이니 30초 뒤 다시 (5번까지).
11. 마지막에 한 줄로: 글 제목, 확인 못 한 것. 환산기는 push 뒤 5분 안에 스킨이 새 데이터를 읽어 뜬다 (스킨에_붙일것.html 이 바뀌었을 때만 다시 붙이라고 알린다)."""


def launcher(request, titles, token):
    day = timezone.localdate()
    rule = concept()
    head = (f"{HEAD} · 글쓰기·변환 · {day.isoformat()} · {len(titles)}작품\n\n"
            "원고 없는 작품의 회차정리 글을 쓰고 서버에 변환 완료로 넣는다. 작품마다 새 터미널에서 차례로 한다.")
    return "\n\n".join([head] + [part(request, a, token, rule) for a in titles])
