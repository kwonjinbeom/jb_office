"""첫 매일 알림 (2026-10-27 사용자: 코스피 장이 끝나는 3시 40분쯤 사이트 안에서 알림). 평일만, 같은 제목이 있으면 넣지 않는다."""
import datetime

from django.db import migrations

TITLE = "코스피 장 마감"


def forward(apps, schema_editor):
    Event = apps.get_model("schedule", "Event")
    if not Event.objects.filter(title=TITLE).exists():
        Event.objects.create(date=datetime.date(2026, 10, 27), time=datetime.time(15, 40), title=TITLE,
                             note="15:30 마감 · 시황 확인", repeat="weekday")


class Migration(migrations.Migration):

    dependencies = [
        ("schedule", "0004_event_repeat"),
    ]

    operations = [migrations.RunPython(forward, migrations.RunPython.noop)]
