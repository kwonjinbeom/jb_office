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
        f"아래 원문을 '{blog.name}'({blog.get_platform_display()}) 사이트에 맞게 바꿔 주세요. 사실·숫자는 바꾸지 말고, 말투·구성·포맷만 바꿉니다.",
        f"## 사이트\n- 이름: {blog.name}\n- 플랫폼: {blog.get_platform_display()}\n- 컨셉: {blog.content or '-'}\n- 넣을 카테고리: {cat}",
        _category_part(cat),
        f"## 사이트 템플릿\n### 말투·멘트\n{tpl.tone or '-'}\n### 구성\n{tpl.structure or '-'}\n### 꼭 지킬 것\n{tpl.rules or '-'}",
        f"## {blog.get_platform_display()} 붙여넣기 포맷\n{fmt.guide or '-'}",
    ]
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
        "1. 그 글의 요청문대로 변환한다. 사실·숫자·링크는 바꾸지 않는다.\n"
        "2. 본문만 `workspace/.routine/convert/<번호>.md` 파일로 쓴다 (UTF-8).\n"
        "3. 아래 '보내기' 명령의 <제목> · <태그> 를 채워 실행한다. 응답이 `ok` 로 시작하면 다음 글.\n"
        "4. 실패하면 이유를 한 줄로 말하고 다음 글로 간다. 다 끝나면 보낸 편수를 한 줄로 말한다.",
    ]
    parts = ["\n\n".join(head)]
    for n, pl in enumerate(placements, start=1):
        url = request.build_absolute_uri(reverse("site_templates:api_save", args=[pl.pk])) + f"?token={token}"
        send = (f'curl -fsS -X POST "{url}" --data-urlencode "title=<제목>" --data-urlencode "tags=<태그>" '
                f'--data-urlencode "body@workspace/.routine/convert/{pl.pk}.md"')
        parts.append(f"---\n\n## 글 {n} · 번호 {pl.pk} · {pl.site_category.blog.name} › {pl.site_category}\n\n"
                     f"보내기:\n```\n{send}\n```\n\n{build(pl)}")
    return "\n\n".join(parts)
