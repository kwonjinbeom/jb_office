"""T84 나루토 환산기 글을 고친 원고로 다시 넣는다 (2026-10-21 사용자: '무인편'이 처음 보는 말이라 이해가 안 간다, 제목은 1등 글처럼 「나루토 회차정리 …」, 표지 사진 자리).

제목이 바뀌었으므로 예전 제목의 글을 새 제목으로 바꾼 뒤 0010 과 같은 일을 한다 (본문·변환본을 새 원고로, 변환 완료).
지우는 데이터는 없다.
"""
from importlib import import_module

from django.db import migrations

OLD = "나루토 애니 몇 화가 만화 몇 화? 무인편·질풍전 환산기"
NEW = "나루토 회차정리 애니만화 환산기 명장면 등 모음"


def forward(apps, schema_editor):
    Post = apps.get_model("writing", "Post")
    if not Post.objects.filter(title=NEW).exists():
        Post.objects.filter(title=OLD).update(title=NEW)
    import_module("apps.writing.migrations.0010_naruto_anime_post").forward(apps, schema_editor)


class Migration(migrations.Migration):

    dependencies = [
        ("writing", "0011_naruto_anime_post_again"),
    ]

    operations = [migrations.RunPython(forward, migrations.RunPython.noop)]
