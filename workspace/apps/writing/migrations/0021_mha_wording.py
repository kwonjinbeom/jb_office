"""나의 히어로 아카데미아 글 고치기 (2026-10-23 사용자): '통산 회차'를 '이어 센 화'로 쉽게, 줄임말은 나히아.
고친 원고(T111)를 place_drafts.place 로 다시 넣는다 (같은 제목 글을 고친다). 지우는 데이터 없음.
"""
from django.db import migrations


def forward(apps, schema_editor):
    from apps.writing.place_drafts import place

    place(apps, "T111_히로아카환산기")


class Migration(migrations.Migration):

    dependencies = [
        ("writing", "0020_anime_fma_mha"),
    ]

    operations = [migrations.RunPython(forward, migrations.RunPython.noop)]
