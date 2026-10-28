"""워드프레스 글 끝 'YYYY-MM-DD 기준, 바뀌면 고칩니다.' 줄 지우기 (2026-10-28 사용자: "이거 지워줘").

- 드라이브·자동차 컨셉의 공통 순서에서 '→ 기준일 줄(…)' 을 뺀다 (0032 가 넣은 것). 앞으로 쓰는 글에 안 생긴다.
- 이미 쓴 워드프레스 글(원고 본문 · 변환본)에서 그 한 줄만 지운다. 다른 내용은 그대로.
  발행한 워드프레스 글은 PC 가 REST 로 같은 줄을 지웠다 — 그래서 '수정됨' 불은 켜지 않는다.
"""
import re

from django.db import migrations

RULE = re.compile(r" → 기준일 줄\('[^']*바뀌면 고칩니다'\)")
LINE = re.compile(r"\s*<p\b[^>]*>\s*\d{4}-\d{2}-\d{2} 기준, 바뀌면 고칩니다\.?\s*</p>"  # HTML 로 저장한 변환본
                  r"|(?:\r?\n)*^\d{4}-\d{2}-\d{2} 기준, 바뀌면 고칩니다\.?[ \t]*(?=\r?$)", re.M)  # 폼으로 저장한 글은 줄바꿈이 \r\n


def forward(apps, schema_editor):
    SiteCategory = apps.get_model("blog_types", "SiteCategory")
    Placement = apps.get_model("blog_types", "Placement")
    Post = apps.get_model("writing", "Post")
    for cat in SiteCategory.objects.filter(blog__platform="wordpress", concept__contains="바뀌면 고칩니다"):
        cat.concept = RULE.sub("", cat.concept)
        cat.save(update_fields=["concept"])
    posts = set()
    for pl in Placement.objects.filter(site_category__blog__platform="wordpress", converted_body__contains="바뀌면 고칩니다"):
        pl.converted_body = LINE.sub("", pl.converted_body)
        pl.save(update_fields=["converted_body"])
        if pl.tistory_post_id:
            posts.add(pl.tistory_post_id)
    for post in Post.objects.filter(pk__in=posts, body__contains="바뀌면 고칩니다"):
        post.body = LINE.sub("", post.body)
        post.save(update_fields=["body"])


class Migration(migrations.Migration):
    dependencies = [
        ("blog_types", "0047_naver_line_tables"),
        ("writing", "0026_trash_nunip_kospi"),
    ]
    operations = [migrations.RunPython(forward, migrations.RunPython.noop)]
