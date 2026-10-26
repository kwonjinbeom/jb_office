"""눈잎에 넣었던 코스피 글을 휴지통으로 (2026-10-26 사용자: 눈잎과 관련 없어 블로그에서 지웠다).

글 관리의 글과 그 넣은 곳(매핑)을 함께. 7일 안에는 휴지통에서 되돌릴 수 있다. 원고 폴더(T60)도 같은 커밋에서 지운다.
"""
from importlib import import_module

from django.db import migrations
from django.utils import timezone

TITLE = "10월 20일 코스피 장중 4%대 하락, 서킷브레이커는 몇 포인트에서 걸리나 (11월 시장 일정 한국시간 표)"


def forward(apps, schema_editor):
    o28 = import_module("apps.blog_types.migrations.0028_sites_overhaul")
    Post = apps.get_model("writing", "Post")
    Placement = apps.get_model("blog_types", "Placement")
    now = timezone.now()
    for post in Post.objects.filter(title=TITLE, deleted_at__isnull=True):
        members = {"writing.post": [post.pk]}
        pls = list(Placement.objects.filter(tistory_post=post, deleted_at__isnull=True).values_list("pk", flat=True))
        if pls:
            members["blog_types.placement"] = pls
        o28._trash(apps, "writing.post", post.pk, post.title, "티스토리 글쓰기", members, now)


class Migration(migrations.Migration):
    dependencies = [
        ("writing", "0025_post_source"),
        ("blog_types", "0030_wordpress_sites"),
        ("core", "0007_posts_hub_menu"),
    ]
    operations = [migrations.RunPython(forward, migrations.RunPython.noop)]
