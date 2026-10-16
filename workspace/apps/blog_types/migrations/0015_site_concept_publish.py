"""사이트 카테고리 컨셉 + 매핑 상태를 미발행 · 발행 완료 둘로 (2026-10-17 사용자).

예전 '임시저장'(draft)은 아직 발행 전이라 미발행(unsaved)으로 바꾼다. 지우는 데이터는 없다.
"""
from django.db import migrations, models


def draft_to_unsaved(apps, schema_editor):
    apps.get_model("blog_types", "Placement").objects.filter(status="draft").update(status="unsaved")


class Migration(migrations.Migration):

    dependencies = [
        ("blog_types", "0014_it_ai_and_changes"),
    ]

    operations = [
        migrations.RunPython(draft_to_unsaved, migrations.RunPython.noop),
        migrations.AddField(
            model_name="sitecategory",
            name="concept",
            field=models.TextField(
                blank=True,
                help_text="이 카테고리 글의 방향·말투·구성 (사이트별 템플릿의 변환 요청문에 사이트 컨셉 다음으로 들어간다)",
                verbose_name="컨셉",
            ),
        ),
        migrations.AlterField(
            model_name="placement",
            name="status",
            field=models.CharField(
                choices=[("unsaved", "미발행"), ("published", "발행 완료")],
                default="unsaved",
                max_length=10,
                verbose_name="상태",
            ),
        ),
    ]
