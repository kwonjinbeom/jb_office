"""0010 을 한 번 더 (2026-10-21). 0010 이 원고.md 보다 먼저 서버에 올라가 원고가 없는 채로 돌았다 (아무것도 안 하고 끝남).

하는 일은 0010 그대로: T84 나루토 환산기 글을 발행예정글로, memorily › 애니 매핑, 변환 완료. 이미 되어 있으면 같은 값으로 다시 쓸 뿐이다.
"""
from importlib import import_module

from django.db import migrations


def forward(apps, schema_editor):
    import_module("apps.writing.migrations.0010_naruto_anime_post").forward(apps, schema_editor)


class Migration(migrations.Migration):

    dependencies = [
        ("writing", "0010_naruto_anime_post"),
    ]

    operations = [migrations.RunPython(forward, migrations.RunPython.noop)]
