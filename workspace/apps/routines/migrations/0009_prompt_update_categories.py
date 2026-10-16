"""프롬프트 최신화가 분류마다 깊은 조사를 하도록 오늘의 자료에 '글 분류 전체'를 더한다 (2026-10-17 사용자:
일일 아이디어·글쓰기는 매일 아침 클라우드 예약으로 돌고, 블로그를 여는 조사는 프롬프트 최신화가 PC 에서 꼼꼼히 해 프롬프트에 쌓는다)."""
from django.db import migrations


def forward(apps, schema_editor):
    Routine = apps.get_model("routines", "Routine")
    for r in Routine.objects.filter(key="prompt_update"):
        keys = [k for k in r.data.split(",") if k]
        if "categories" not in keys:
            r.data = ",".join(keys + ["categories"])
            r.save(update_fields=["data"])


class Migration(migrations.Migration):
    dependencies = [("routines", "0008_one_writing_routine")]
    operations = [migrations.RunPython(forward, migrations.RunPython.noop)]
