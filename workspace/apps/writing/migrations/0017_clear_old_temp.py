"""임시글 정리 (2026-10-22 사용자): 커스텀 글과 오늘(2026-10-22) 만든 글만 남기고 임시글은 모두 휴지통으로.

티스토리·네이버 두 표 모두. 휴지통이라 7일 안에는 복원할 수 있다. 넣은 곳(Placement)이 있으면 함께 옮긴다.
"""
from datetime import date

from django.db import migrations
from django.utils import timezone

KEEP_DAY = date(2026, 10, 22)
SECTIONS = {"writing": "티스토리 글쓰기 · 임시글", "naver_writing": "네이버 글쓰기 · 임시글"}


def forward(apps, schema_editor):
    TrashEntry = apps.get_model("core", "TrashEntry")
    Placement = apps.get_model("blog_types", "Placement")
    now = timezone.now()
    for label, section in SECTIONS.items():
        Post = apps.get_model(label, "Post")
        field = "tistory_post" if label == "writing" else "naver_post"
        for post in Post.objects.filter(stage="temp", custom=False, deleted_at__isnull=True):
            if timezone.localtime(post.created_at).date() == KEEP_DAY:
                continue
            places = list(Placement.objects.filter(**{field: post}, deleted_at__isnull=True).values_list("pk", flat=True))
            members = {f"{label}.post": [post.pk]}
            if places:
                members["blog_types.placement"] = places
            TrashEntry.objects.filter(model_label=f"{label}.post", object_key=str(post.pk)).delete()
            TrashEntry.objects.create(model_label=f"{label}.post", object_key=str(post.pk), title=(post.title or "글")[:200],
                                      section=section, deleted_at=now, members=members)
            Post.objects.filter(pk=post.pk).update(deleted_at=now)
            Placement.objects.filter(pk__in=places).update(deleted_at=now)


class Migration(migrations.Migration):
    dependencies = [
        ("writing", "0016_post_custom"),
        ("naver_writing", "0007_post_custom"),
        ("blog_types", "0017_simple_classes"),
        ("core", "0002_sourceexclusion_trashentry"),
    ]
    operations = [migrations.RunPython(forward, migrations.RunPython.noop)]
