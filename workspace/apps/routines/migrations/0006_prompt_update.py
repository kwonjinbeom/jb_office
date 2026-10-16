"""일일루틴 리스트에 '프롬프트 최신화' 루틴 (2026-10-16 사용자: 프롬프트 관리의 갱신을 리스트의 한 줄로).

평가·점검 관점(오늘의 자료 evaluations)을 보고 각 루틴의 프롬프트 md 를 고친다. 이미 있으면 두지 않는다.
"""
from django.db import migrations


def forward(apps, schema_editor):
    Routine = apps.get_model("routines", "Routine")
    if Routine.objects.filter(key="prompt_update").exists():
        return
    order = max(Routine.objects.values_list("order", flat=True), default=0) + 1
    Routine.objects.create(
        key="prompt_update", name="프롬프트 최신화", url_name="routines:prompts", order=order,
        task="평가·점검 관점으로 루틴 프롬프트 md 고치기", output="일일루틴/프롬프트/*.md", daily=1, unit="회",
        prompt_doc="일일루틴/프롬프트/prompt_update.md", data="evaluations",
        review_focus="고친 프롬프트가 다음 결과에서 실제로 나아졌는지(평점 변화), 지시가 길어지거나 서로 부딪히지 않는지.")


class Migration(migrations.Migration):
    dependencies = [("routines", "0005_prompt_docs")]
    operations = [migrations.RunPython(forward, migrations.RunPython.noop)]
