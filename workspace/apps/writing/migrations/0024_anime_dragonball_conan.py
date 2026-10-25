"""애니 총정리 두 편 넣기 (2026-10-25 사용자): 드래곤볼(T139)·명탐정 코난(T140).
place_drafts.place 로 발행예정글 + memorily › 애니 매핑 + 변환 완료, 애니 총정리 목록의 두 작품을 '원고 완료'로 바꾸고 작품 md 와 잇는다.
지우는 데이터 없음.
"""
from django.db import migrations

DRAFTS = (("T139_드래곤볼환산기", "드래곤볼", "09_드래곤볼"), ("T140_명탐정코난환산기", "명탐정 코난", "10_명탐정코난"))


def forward(apps, schema_editor):
    from apps.writing.place_drafts import place

    AnimeTitle = apps.get_model("anime", "AnimeTitle")
    for folder, title, doc in DRAFTS:
        if place(apps, folder):
            AnimeTitle.objects.filter(title=title, deleted_at__isnull=True).update(status="written", doc_key=doc, picked=True)


class Migration(migrations.Migration):

    dependencies = [
        ("writing", "0023_anime_aot_kny"),
        ("anime", "0004_concept_calc_data_outside_skin"),
    ]

    operations = [migrations.RunPython(forward, migrations.RunPython.noop)]
