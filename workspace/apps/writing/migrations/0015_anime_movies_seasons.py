"""애니 총정리 네 편 고치기 (2026-10-21 사용자): 헌터×헌터 1999·2011이 왜 나뉘었는지, 블리치 몇 기(16기),
극장판·보는 순서(나루토·블리치·헌터×헌터·원피스). 원고를 고쳤으니 place_drafts.place 로 글·변환본을 원고대로 다시 채운다.
같은 제목 글을 고친다. 매핑의 발행 상태는 건드리지 않는다. 지우는 데이터 없음.
"""
from django.db import migrations

FOLDERS = ("T84_나루토환산기", "T85_블리치환산기", "T86_헌터헌터환산기", "T87_원피스환산기")


def forward(apps, schema_editor):
    from apps.writing.place_drafts import place

    for folder in FOLDERS:
        place(apps, folder)


class Migration(migrations.Migration):

    dependencies = [
        ("writing", "0014_anime_three_posts"),
    ]

    operations = [migrations.RunPython(forward, migrations.RunPython.noop)]
