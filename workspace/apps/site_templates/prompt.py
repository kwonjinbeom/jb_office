"""변환 요청문: 사이트 템플릿 + 카테고리 컨셉 + 플랫폼 포맷 + 원문을 한 덩어리로.

- build: 글 하나의 요청문 (변환 화면의 '요청문' 복사, requests.json).
- launcher: 사이트별 템플릿의 '변환'·'전체 변환'이 PC 터미널의 claude 에게 주는 안내문 (여러 편을 차례로 변환하고
  변환본을 서버의 저장 주소로 curl 로 보낸다. apps/routines/local_run.py 의 convert 실행).
"""
from django.urls import reverse
from django.utils import timezone

from . import paste
from .models import PlatformFormat, SiteTemplate

LAUNCH_HEAD = "# 사이트 변환"  # local_run 이 이걸로 변환 안내문인지 본다

# 변환 때 사실 점검 (2026-10-20 사용자: 변환할 때 숫자·날짜·일정을 출처에서 다시 확인하고, 틀린 건 고치고, 무엇을 왜 고쳤는지
# 출처와 함께 변환 화면에 남긴다). 기록은 Placement.converted_check, 꼴은 paste.OUTPUT 의 '점검 기록'.
FACT_CHECK = """## 사실 점검 (변환할 때 꼭)
- 원문의 숫자·날짜·일정·기준값(지수·금리·금액·조건·시간)을 하나씩 출처에서 다시 확인한다 (웹 검색·브라우저). 공식 출처(기관·거래소·회사 발표)를 먼저, 없으면 믿을 만한 보도.
- 틀린 것은 변환본에서 고친다. 확인되지 않거나 아직 안 나온 일정은 '미정'으로 둔다. 추측으로 채우지 않는다.
- 맞는 것은 그대로 둔다. 원문에 없는 숫자·주장을 새로 더하지 않는다.
- 무엇을 왜 고쳤는지 출처 주소와 함께 '점검 기록'으로 남긴다 (아래 '돌려줄 것')."""


# 변환 때 사진 찾아 넣기 (2026-10-20 사용자: 사진 자리를 비워 두지 말고 변환할 때 찾아 넣는다).
# 저작권 때문에 상업적 사용이 무료인 사진 사이트만. 워드프레스는 빼고 (미디어 라이브러리에 올려야 한다)
# 네이버는 붙여넣기로 사진이 안 옮겨지지만 변환 화면에 사진이 보이니 내려받아 그 자리에 올린다 (2026-10-20 사용자).
PHOTO_PLATFORMS = {"tistory", "blogger", "naver"}
PHOTOS = """## 사진 (변환할 때 찾아 넣기)
- 원문의 [사진: 설명]·📷 자리마다 내용에 맞는 사진을 찾아 넣는다. 자리가 없으면 소제목 두세 개마다 한 장, 글 전체 1~3장.
- 쓸 곳은 Unsplash · Pexels · Pixabay 만 (상업적 사용 무료, 허락 필요 없음). 구글 이미지 검색·핀터레스트·뉴스 사진·다른 블로그·기관 홈페이지 사진은 저작권 때문에 쓰지 않는다 (핀터레스트는 남의 사진을 퍼 온 것이라 쓸 권리가 없다).
- 사진 페이지에서 이미지 파일 주소(images.unsplash.com · images.pexels.com · cdn.pixabay.com)를 찾아 `![설명](https://주소)` 한 줄로 넣는다. Unsplash·Pexels 는 주소 끝에 너비(w=1200)를 붙인다.
- 바로 다음 줄에 출처 캡션 `*사진: 작가 이름 · Unsplash*`.
- 분위기·대상을 보여 주는 사진만 (병원, 달력, 주사 장면 같은 것). 숫자·일정이 든 그림처럼 쓰지 않는다. 상표·실존 인물 얼굴이 중심인 사진은 피한다.
- 직접 찍어야 하는 사진(내 경험·현장)이나 맞는 사진이 없으면 [사진: 설명] 자리를 그대로 둔다. 표·도식으로 만들 그림은 [그림: 파일명] 자리로 둔다.
- 점검 기록에 `- 사진: 설명 · 사진 페이지 주소` 로 한 장씩 남긴다."""


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
        f"아래 원문을 '{blog.name}'({blog.get_platform_display()}) 사이트에 맞게 바꿔 주세요. 말투·구성·포맷을 바꾸고, "
        "숫자·날짜·일정은 출처에서 다시 확인해 틀린 것만 고칩니다 (아래 '사실 점검').",
        f"## 사이트\n- 이름: {blog.name}\n- 플랫폼: {blog.get_platform_display()}\n- 컨셉: {blog.content or '-'}\n- 넣을 카테고리: {cat}",
        _category_part(cat),
        f"## 사이트 템플릿\n### 말투·멘트\n{tpl.tone or '-'}\n### 구성\n{tpl.structure or '-'}\n### 꼭 지킬 것\n{tpl.rules or '-'}",
        f"## {blog.get_platform_display()} 붙여넣기 포맷\n{fmt.guide or '-'}",
    ]
    parts.append(FACT_CHECK)
    if blog.platform in PHOTO_PLATFORMS:
        parts.append(PHOTOS)
    if placement.convert_note:
        parts.append(f"## 이 글만\n{placement.convert_note}")
    parts.append(f"## 원문\n### 제목\n{post.title}\n### 본문\n{post.body}")
    parts.append(paste.OUTPUT)
    return "\n\n".join(p for p in parts if p)


def _category_part(cat):
    """카테고리 컨셉 (하위 카테고리면 위 카테고리 것부터). 없으면 빈 값."""
    lines = [f"- {c.name}: {c.concept.strip()}" for c in (cat.parent, cat) if c is not None and c.concept.strip()]
    return "## 카테고리 컨셉\n" + "\n".join(lines) if lines else ""


def launcher(request, placements, token):
    """PC 터미널 claude 에게 줄 안내문: 글마다 요청문대로 변환 → 본문 파일 → 서버 저장 주소로 curl."""
    day = timezone.localdate()
    head = [
        f"{LAUNCH_HEAD} · {day.isoformat()} · {len(placements)}편",
        "아래 글을 각 사이트·카테고리에 맞게 변환하고 변환본을 서버로 보낸다. 사용자에게 묻지 않고 끝까지 한다. "
        "git 커밋·push 는 하지 않는다 (변환본은 서버 DB 에만 들어간다).",
        "## 글마다 하는 일\n"
        "1. 그 글의 요청문대로 변환한다. 숫자·날짜·일정은 요청문의 '사실 점검'대로 출처에서 다시 확인하고 틀린 것만 고친다. 링크는 바꾸지 않는다.\n"
        "2. 본문만 `workspace/.routine/convert/<번호>.md`, 점검 기록은 `workspace/.routine/convert/<번호>-check.md` 파일로 쓴다 (UTF-8).\n"
        "3. 아래 '보내기' 명령의 <제목> · <태그> 를 채워 실행한다. 응답이 `ok` 로 시작하면 다음 글.\n"
        "4. 실패하면 이유를 한 줄로 말하고 다음 글로 간다. 다 끝나면 보낸 편수와 고친 곳 수를 한 줄로 말한다.",
    ]
    parts = ["\n\n".join(head)]
    for n, pl in enumerate(placements, start=1):
        url = request.build_absolute_uri(reverse("site_templates:api_save", args=[pl.pk])) + f"?token={token}"
        send = (f'curl -fsS -X POST "{url}" --data-urlencode "title=<제목>" --data-urlencode "tags=<태그>" '
                f'--data-urlencode "body@workspace/.routine/convert/{pl.pk}.md" '
                f'--data-urlencode "check@workspace/.routine/convert/{pl.pk}-check.md"')
        parts.append(f"---\n\n## 글 {n} · 번호 {pl.pk} · {pl.site_category.blog.name} › {pl.site_category}\n\n"
                     f"보내기:\n```\n{send}\n```\n\n{build(pl)}")
    return "\n\n".join(parts)
