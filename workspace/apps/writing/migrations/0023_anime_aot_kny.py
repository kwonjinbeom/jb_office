"""애니 총정리 두 편 넣기 (2026-10-23 사용자): 진격의 거인(T120)·귀멸의 칼날(T121).
place_drafts.place 로 발행예정글 + memorily › 애니 매핑 + 변환 완료, 애니 총정리 목록의 두 작품을 '원고 완료'로 바꾸고 작품 md 와 잇는다.
지우는 데이터 없음.
"""
from django.db import migrations

DRAFTS = (("T120_진격의거인환산기", "진격의 거인", "07_진격의거인"), ("T121_귀멸의칼날환산기", "귀멸의 칼날", "08_귀멸의칼날"))


def forward(apps, schema_editor):
    from apps.writing.place_drafts import place

    AnimeTitle = apps.get_model("anime", "AnimeTitle")
    for folder, title, doc in DRAFTS:
        if place(apps, folder):
            AnimeTitle.objects.filter(title=title, deleted_at__isnull=True).update(status="written", doc_key=doc, picked=True)


class Migration(migrations.Migration):

    dependencies = [
        ("writing", "0022_rewrite_t112"),
        ("anime", "0003_memorily_anime_concept"),
    ]

    operations = [migrations.RunPython(forward, migrations.RunPython.noop)]
