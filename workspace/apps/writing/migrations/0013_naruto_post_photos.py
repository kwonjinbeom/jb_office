"""T84 나루토 글에 사진을 녹인 원고로 변환본을 다시 채운다 (2026-10-21 사용자: 표지·장면 사진을 글에 자연스럽게, 변환 화면에 바로).

하는 일은 0010 그대로 (본문·변환본을 원고로, 변환 완료). 지우는 데이터는 없다.
"""
from importlib import import_module

from django.db import migrations


def forward(apps, schema_editor):
    import_module("apps.writing.migrations.0010_naruto_anime_post").forward(apps, schema_editor)


class Migration(migrations.Migration):

    dependencies = [
        ("writing", "0012_naruto_post_easier_words"),
    ]

    operations = [migrations.RunPython(forward, migrations.RunPython.noop)]
