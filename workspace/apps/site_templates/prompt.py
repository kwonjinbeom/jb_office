"""변환 요청문: 사이트 템플릿 + 플랫폼 포맷 + 원문을 한 덩어리로. 사용자가 복사해 Claude 에게 주거나, Claude 가 requests.json 으로 읽는다."""
from .models import PlatformFormat, SiteTemplate


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
        f"## 사이트 템플릿\n### 말투·멘트\n{tpl.tone or '-'}\n### 구성\n{tpl.structure or '-'}\n### 꼭 지킬 것\n{tpl.rules or '-'}",
        f"## {blog.get_platform_display()} 붙여넣기 포맷\n{fmt.guide or '-'}",
    ]
    if placement.convert_note:
        parts.append(f"## 이 글만\n{placement.convert_note}")
    parts.append(f"## 원문\n### 제목\n{post.title}\n### 본문\n{post.body}")
    parts.append("## 돌려줄 것\n변환 제목 한 줄, 변환 본문 (마크다운 또는 HTML).")
    return "\n\n".join(parts)
