"""커스텀 글쓰기 'AI 소식'은 한 번에 1편 (2026-10-22 사용자: 왜 7편이야). 지침의 '매일 한 편'도 '한 편'으로."""
from django.db import migrations


def forward(apps, schema_editor):
    FixedTopic = apps.get_model("routines", "FixedTopic")
    for topic in FixedTopic.objects.filter(name="AI 소식", deleted_at__isnull=True):
        topic.per_week = 1
        topic.note = topic.note.replace("매일 한 편. 사용자가 AI 최신 소식을", "한 번에 한 편. 사용자가 AI 최신 소식을", 1)
        topic.save(update_fields=["per_week", "note"])


class Migration(migrations.Migration):
    dependencies = [("routines", "0016_writing_by_material"), ("blog_types", "0018_site_cleanup")]
    operations = [migrations.RunPython(forward, migrations.RunPython.noop)]
