"""글쓰기 루틴 할 일 문구 (2026-10-22 사용자): 사이트별 고정 소재 중 오늘 소재가 있는 것만 쓴다 (화면에서 고친 문구는 그대로)."""
from django.db import migrations

OLD = "운영 사이트 컨셉에 맞게, 고른 분류별 원고 쓰기"
NEW = "사이트별 고정 소재 중 오늘 소재가 있는 것만 원고 쓰기"


def forward(apps, schema_editor):
    apps.get_model("routines", "Routine").objects.filter(key="writing", task=OLD).update(task=NEW)


class Migration(migrations.Migration):
    dependencies = [("routines", "0015_topic_feedback_titles")]
    operations = [migrations.RunPython(forward, migrations.RunPython.noop)]
