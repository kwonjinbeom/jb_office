"""첫 일정 (2026-10-22 사용자: 블리치 천년혈전 50화 방영 뒤 갱신 일정을 잡아 둔다). 같은 제목이 있으면 넣지 않는다."""
import datetime

from django.db import migrations

EVENTS = [
    (datetime.date(2026, 10, 28), "블리치 천년혈전 50화 데이터 갱신",
     "10월 26~27일 방영된 천년혈전 50화(최종)의 만화 범위 확인 → 애니환산기/data/bleach.json 에 50화 추가 → build.py → "
     "스킨에_붙일것.html 다시 붙이기 · T85 블리치 글의 '방영 예정' 문구 고치기 (애니 총정리 › 02_블리치)"),
]


def forward(apps, schema_editor):
    Event = apps.get_model("schedule", "Event")
    for day, title, note in EVENTS:
        if not Event.objects.filter(title=title).exists():
            Event.objects.create(date=day, title=title, note=note)


class Migration(migrations.Migration):

    dependencies = [
        ("schedule", "0001_initial"),
    ]

    operations = [migrations.RunPython(forward, migrations.RunPython.noop)]
