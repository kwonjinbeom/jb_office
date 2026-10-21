"""애니 총정리 세 편(블리치·헌터×헌터·원피스)을 발행예정글로 넣고 memorily › 애니 에 매핑, 변환 완료 (2026-10-21 사용자).

나루토(0010)와 같은 일을 place_drafts.place 로 한다. 원고와 같은 커밋에 들어간다. 지우는 데이터는 없다.
"""
from django.db import migrations

FOLDERS = ("T85_블리치환산기", "T86_헌터헌터환산기", "T87_원피스환산기")


def forward(apps, schema_editor):
    from apps.writing.place_drafts import place

    for folder in FOLDERS:
        place(apps, folder)


class Migration(migrations.Migration):

    dependencies = [
        ("writing", "0013_naruto_post_photos"),
        ("blog_types", "0016_placement_converted_check"),
        ("blog_rules", "0008_site_day"),
    ]

    operations = [migrations.RunPython(forward, migrations.RunPython.noop)]
