"""이미 들어온 글의 '만든 날'을 그 글의 글쓰기 날짜로 (2026-10-28 사용자: 29일로 미리 쓴 글이 28일 횟수·결과에 들어갔다).

원고의 '발행 예정' 줄 또는 그날 기획표(주제기획/<날짜>.md)의 `### T번호 · 사이트 > 소재` 로 그 글이 어느 날 분량인지 찾아
날짜만 그 날로 바꾼다 (시각은 그대로). 원고 폴더가 없거나 기획에 없는 글(애니·커스텀)은 그대로. 지우는 데이터 없음.
"""
from django.db import migrations
from django.utils import timezone


def forward(apps, schema_editor):
    from apps.writing import drafts

    Post = apps.get_model("writing", "Post")
    by_key = {d.key: d for d in drafts.list_drafts()}
    for post in Post.objects.exclude(source="").only("pk", "source", "created_at"):
        d = by_key.get(post.source)
        day = drafts.plan_day(d) if d else None
        if day and timezone.localtime(post.created_at).date() != day:
            Post.objects.filter(pk=post.pk).update(created_at=drafts.on_day(post.created_at, day))


class Migration(migrations.Migration):
    dependencies = [("writing", "0026_trash_nunip_kospi")]
    operations = [migrations.RunPython(forward, migrations.RunPython.noop)]
