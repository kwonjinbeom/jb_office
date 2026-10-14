"""논의에 '등록' 날짜를 둔다. 이미 있는 논의는 첫 요약 이력(없으면 최근 변경) 시각으로 채운다."""
import django.utils.timezone
from django.db import migrations, models
from django.db.models import Min


def backfill(apps, schema_editor):
    Discussion = apps.get_model("discussions", "Discussion")
    for item in Discussion.objects.annotate(first=Min("history__created_at")):
        item.created_at = min(filter(None, [item.first, item.updated_at]))
        item.save(update_fields=["created_at"])


class Migration(migrations.Migration):
    dependencies = [("discussions", "0001_initial")]
    operations = [
        migrations.AddField(
            model_name="discussion",
            name="created_at",
            field=models.DateTimeField(default=django.utils.timezone.now, editable=False, verbose_name="등록"),
        ),
        migrations.AlterField(
            model_name="discussion",
            name="updated_at",
            field=models.DateTimeField(auto_now=True, verbose_name="최근 변경"),
        ),
        migrations.RunPython(backfill, migrations.RunPython.noop),
    ]
