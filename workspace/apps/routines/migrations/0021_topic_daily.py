"""고정 주제 '매일 전체 실행' (2026-10-23 사용자): AI 소식을 일일루틴 전체 실행(글쓰기)에서 매일 1편."""
from django.db import migrations, models


def forward(apps, schema_editor):
    apps.get_model("routines", "FixedTopic").objects.filter(name="AI 소식", deleted_at__isnull=True).update(daily=True)


class Migration(migrations.Migration):
    dependencies = [("routines", "0020_topics_under_materials")]
    operations = [
        migrations.AddField(
            model_name="fixedtopic", name="daily",
            field=models.BooleanField(default=False, help_text="일일루틴 전체 실행(글쓰기)에서 매일 1편 쓴다 (2026-10-23 사용자: AI 소식)",
                                      verbose_name="매일 전체 실행"),
        ),
        migrations.RunPython(forward, migrations.RunPython.noop),
    ]
