"""2026년 1~3분기 방영작 (2026-10-23 사용자: 우선 26년만). data/2026.json — ani.ohli24.com 의 2026 완결·방영중 목록에서
방영 시작일로 분기를 나눴다 (4분기는 아직 방영 중이라 뺐다). 같은 연도·분기·제목이 있으면 넣지 않는다."""
import datetime
import json
from pathlib import Path

from django.db import migrations

DATA = Path(__file__).resolve().parent.parent / "data" / "2026.json"


def forward(apps, schema_editor):
    SeasonAnime = apps.get_model("anime_seasons", "SeasonAnime")
    for row in json.loads(DATA.read_text(encoding="utf-8")):
        aired = datetime.date.fromisoformat(row["aired"])
        if SeasonAnime.objects.filter(year=aired.year, quarter=row["q"], title=row["title"]).exists():
            continue
        SeasonAnime.objects.create(year=aired.year, quarter=row["q"], title=row["title"], original_title=row["orig"],
                                   aired=aired, genre=row["genre"], episodes=row["episodes"])


class Migration(migrations.Migration):

    dependencies = [
        ("anime_seasons", "0001_initial"),
    ]

    operations = [migrations.RunPython(forward, migrations.RunPython.noop)]
