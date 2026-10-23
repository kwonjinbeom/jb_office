"""memorily › 애니 카테고리 컨셉의 '환산기' 두 줄을 고친다 (2026-10-24: 작품 데이터를 스킨에 넣지 않고 저장소의 환산기데이터.json 을
읽게 바꿨다. 새 작품은 push 만 하면 뜨고 스킨은 다시 붙이지 않는다).

0003 이 넣은 두 줄이 그대로 있을 때만 바꾼다. 사용자가 고쳤으면 건드리지 않는다. 지우는 데이터 없음.
"""
from django.db import migrations

OLD = """- 데이터는 `애니환산기/data/<작품키>.json` (회차마다 [만화 첫 화, 끝 화, 종류 1 원작 · 2 원작+애니 · 0 오리지널]), `build.py` 로 스킨 파일을 다시 만든다.
- 새 작품 환산기는 티스토리 스킨에 `스킨에_붙일것.html` 을 다시 붙여야 뜬다."""
NEW = """- 데이터는 `애니환산기/data/<작품키>.json` (회차마다 [만화 첫 화, 끝 화, 종류 1 원작 · 2 원작+애니 · 0 오리지널], 줄임말은 `alias`), `build.py` 로 `환산기데이터.json` 을 다시 만든다.
- 스킨의 환산기가 main 의 `환산기데이터.json` 을 읽으므로 새 작품은 push 하면 뜬다. 스킨(`스킨에_붙일것.html`)은 환산기 화면 · 글모양이 바뀌었을 때만 다시 붙인다."""


def forward(apps, schema_editor):
    SiteCategory = apps.get_model("blog_types", "SiteCategory")
    for cat in SiteCategory.objects.filter(concept__contains=OLD):
        cat.concept = cat.concept.replace(OLD, NEW)
        cat.save(update_fields=["concept"])


class Migration(migrations.Migration):

    dependencies = [
        ("anime", "0003_memorily_anime_concept"),
    ]

    operations = [migrations.RunPython(forward, migrations.RunPython.noop)]
