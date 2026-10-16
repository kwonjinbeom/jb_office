"""글 분류에 대분류 'IT/AI' (2026-10-16 사용자) + AI 분류 변경 기록 표.

IT/AI 아래 중분류 셋: AI 도구·활용 · 개발·코딩 · IT 소식·제품. 이미 있으면 두지 않는다.
"""
from django.db import migrations, models

CATS = [
    ("A", "AI 도구·활용", "새 AI 도구를 실제로 써 보고 싶어서", "이 AI 로 내 일을 어떻게 줄이지?"),
    ("B", "개발·코딩", "개발하다 막힌 걸 풀거나 배우려고", "이 에러·기능은 어떻게 하지?"),
    ("C", "IT 소식·제품", "새 기술·제품이 나에게 무슨 의미인지 알고 싶어서", "이번에 나온 게 뭐가 달라졌지?"),
]


def forward(apps, schema_editor):
    Section = apps.get_model("blog_types", "Section")
    Category = apps.get_model("blog_types", "Category")
    if Section.objects.filter(name="IT/AI", deleted_at__isnull=True).exists():
        return
    order = (Section.objects.aggregate(m=models.Max("order"))["m"] or 0) + 1
    section = Section.objects.create(name="IT/AI", order=order, note="IT·AI 정보 글 (도구 활용, 개발, 기술 소식)")
    for i, (code, name, direction, question) in enumerate(CATS, start=1):
        Category.objects.create(section=section, code=code, name=name, direction=direction, question=question, order=i)


class Migration(migrations.Migration):
    dependencies = [("blog_types", "0013_placement_tags")]
    operations = [
        migrations.CreateModel(
            name="ClassChange",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=120, unique=True, verbose_name="파일")),
                ("applied_at", models.DateTimeField(auto_now_add=True, verbose_name="반영한 때")),
                ("ok", models.BooleanField(default=True, verbose_name="모두 반영")),
                ("log", models.TextField(blank=True, verbose_name="결과")),
            ],
            options={"verbose_name": "분류 변경 기록", "verbose_name_plural": "분류 변경 기록", "ordering": ["-applied_at", "-pk"]},
        ),
        migrations.RunPython(forward, migrations.RunPython.noop),
    ]
