"""커스텀 글쓰기를 사이트별로 (2026-10-23 사용자): 사이트를 비워 둔 처음 고정 주제(공모주·청년·신혼 정책·청약 공고)는
모두 눈잎 주제라 눈잎 아래로 모은다 (writing.md '사이트별 타겟'). 화면에서 사이트를 정한 주제는 그대로 둔다. 지우는 데이터는 없다."""
from django.db import migrations

NAMES = ["공모주 일정 · 국내", "공모주 일정 · 해외", "청년·신혼 정책 (서울·경기)", "청약·임대주택 공고 (서울·경기)"]


def forward(apps, schema_editor):
    apps.get_model("routines", "FixedTopic").objects.filter(name__in=NAMES, site="").update(site="눈잎")


def backward(apps, schema_editor):
    apps.get_model("routines", "FixedTopic").objects.filter(name__in=NAMES, site="눈잎").update(site="")


class Migration(migrations.Migration):
    dependencies = [("routines", "0018_topic_material_first")]
    operations = [migrations.RunPython(forward, backward)]
