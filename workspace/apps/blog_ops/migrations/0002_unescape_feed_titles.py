"""RSS 제목 바로잡기 (2026-10-23 사용자: 모니터링에서 눈잎 어제 숫자가 안 맞는다).

티스토리 RSS 는 '청약&amp;middot;환불' 처럼 한 번 더 감싸 보내서, 저장된 제목에 '&middot;' 가 글자로 남았다.
그래서 같은 글이 다른 제목이 되어 두 번 세어졌다 (RSS 의 어제 + 글 관리에서 오늘 누른 발행 완료).
1. 저장된 RSS 제목의 엔티티를 푼다.
2. 이미 발행 완료로 바꾼 글 중 같은 제목의 RSS 글이 더 이른 날 올라왔으면 발행일을 그날로 당긴다 (feeds.align_dates 와 같은 규칙).
지우는 데이터 없음.
"""
import html
import re

from django.db import migrations
from django.utils import timezone


def _norm(title):
    return re.sub(r"[\s\"'“”‘’·]", "", html.unescape(title or "")).lower()


def forward(apps, schema_editor):
    FeedEntry = apps.get_model("blog_ops", "FeedEntry")
    Blog = apps.get_model("blog_rules", "Blog")
    Placement = apps.get_model("blog_types", "Placement")
    models = {"writing": apps.get_model("writing", "Post"), "naver_writing": apps.get_model("naver_writing", "Post")}

    for e in FeedEntry.objects.filter(title__contains="&"):
        clean = html.unescape(e.title)
        if clean != e.title:
            FeedEntry.objects.filter(pk=e.pk).update(title=clean[:300])

    for blog in Blog.objects.all():
        first = {}  # 제목 → RSS 에 처음 올라온 날
        for e in FeedEntry.objects.filter(blog=blog):
            day = timezone.localtime(e.published_at).date()
            key = _norm(e.title)
            if key not in first or day < first[key]:
                first[key] = day
        if not first:
            continue
        posts = []
        for pl in Placement.objects.filter(site_category__blog=blog, status="published"):
            for label, field in (("writing", "tistory_post_id"), ("naver_writing", "naver_post_id")):
                pk = getattr(pl, field)
                if pk:
                    post = models[label].objects.filter(pk=pk).first()
                    if post:
                        posts.append((post, {pl.converted_title, post.title}))
        for model in models.values():
            for post in model.objects.filter(publish_status="done", target=blog.name, placements__isnull=True):
                posts.append((post, {post.title}))
        for post, titles in posts:
            days = [first[_norm(t)] for t in titles if t and _norm(t) in first]
            if days and post.published_on and post.published_on > min(days):
                type(post).objects.filter(pk=post.pk).update(published_on=min(days))


class Migration(migrations.Migration):
    dependencies = [
        ("blog_ops", "0001_initial"),
        ("blog_rules", "0009_site_targets"),
        ("blog_types", "0020_site_links"),
        ("writing", "0021_mha_wording"),
        ("naver_writing", "0008_post_planned_on"),
    ]
    operations = [migrations.RunPython(forward, migrations.RunPython.noop)]
