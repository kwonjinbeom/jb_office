"""글 분류 눈잎 · black_lukey(네이버 블로그) › '그 외' 소재를 휴지통으로 (2026-10-31 사용자: 템플릿도 없는데 왜 있나).

눈잎 '그 외'는 0019 가 소재 순서를 정할 때 "위 소재 밖의 강한 소재" 자리로 둔 것인데, 그 소재를 받을 사이트 카테고리·템플릿이
없어 글쓰기 목록에만 남아 있었다. 소재(와 그 아래 글 틀)만 휴지통으로 — 7일 안에는 휴지통에서 되돌린다.
이미 그 분류로 쓴 글은 그대로 둔다 (글 관리·발행 기록 유지). 밤밤 '그 외'는 0028 에서 이미 뺐다.
blog_types 가 아니라 여기 두는 것은 다른 작업의 blog_types migration 번호와 부딪히지 않게 하려고.
"""
from django.db import migrations
from django.utils import timezone

SITES = ("눈잎", "black_lukey")


def forward(apps, schema_editor):
    Category = apps.get_model("blog_types", "Category")
    PostType = apps.get_model("blog_types", "PostType")
    SubType = apps.get_model("blog_types", "SubType")
    TrashEntry = apps.get_model("core", "TrashEntry")
    now = timezone.now()
    for cat in Category.objects.filter(section__name__in=SITES, name="그 외", deleted_at__isnull=True).select_related("section"):
        types = list(PostType.objects.filter(category=cat, deleted_at__isnull=True).values_list("pk", flat=True))
        subs = list(SubType.objects.filter(post_type__in=types, deleted_at__isnull=True).values_list("pk", flat=True))
        members = {"blog_types.category": [cat.pk]}
        if types:
            members["blog_types.posttype"] = types
        if subs:
            members["blog_types.subtype"] = subs
        TrashEntry.objects.filter(model_label="blog_types.category", object_key=str(cat.pk)).delete()
        TrashEntry.objects.create(model_label="blog_types.category", object_key=str(cat.pk), title=f"{cat.section.name} › {cat.name}",
                                  section="카테고리 관리 · 카테고리", deleted_at=now, members=members)
        Category.objects.filter(pk=cat.pk).update(deleted_at=now)
        PostType.objects.filter(pk__in=types).update(deleted_at=now)
        SubType.objects.filter(pk__in=subs).update(deleted_at=now)


class Migration(migrations.Migration):
    dependencies = [
        ("routines", "0021_topic_daily"),
        ("blog_types", "0053_black_lukey_sale_event"),  # 세일 이벤트를 되살린 뒤
        ("core", "0007_posts_hub_menu"),
    ]
    operations = [migrations.RunPython(forward, migrations.RunPython.noop)]
