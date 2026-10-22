"""애니 총정리 두 편 넣기 (2026-10-22 사용자): 강철의 연금술사(T110)·나의 히어로 아카데미아(T111).
place_drafts.place 로 발행예정글 + memorily › 애니 매핑 + 변환 완료. 지우는 데이터 없음.
"""
from django.db import migrations

FOLDERS = ("T110_강철의연금술사환산기", "T111_히로아카환산기")


def forward(apps, schema_editor):
    from apps.writing.place_drafts import place

    for folder in FOLDERS:
        place(apps, folder)


class Migration(migrations.Migration):

    dependencies = [
        ("writing", "0019_post_planned_on"),
        ("blog_types", "0019_nunip_site_categories"),
        ("blog_rules", "0009_site_targets"),
    ]

    operations = [migrations.RunPython(forward, migrations.RunPython.noop)]
