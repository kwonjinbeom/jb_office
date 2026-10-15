"""첫 대분류 '판매 수익 (커넥트)'를 만들고, 지금 있는 카테고리(A~G 등)를 모두 그 아래로 옮긴다.

2026-10-15 사용자: A~G 는 블로그에 표시할 카테고리가 아니라 쇼핑커넥트·판매 수익을 위한 방향이다.
일상·브이로그·맛집 같은 블로그 표시 분류는 화면에서 다른 대분류로 추가한다.
화면에서 고친 카테고리 값은 그대로 두고 소속만 정한다.
"""
from django.db import migrations, models

NOTE = ("블로그에 표시하는 카테고리가 아니라 쇼핑커넥트·쿠팡파트너스 판매 수익을 위한 방향이다. "
        "찍어내기 계정용. 카테고리는 사게 만드는 방향, 나누는 기준은 글을 연 사람의 질문.")


def forward(apps, schema_editor):
    Section = apps.get_model("blog_types", "Section")
    Category = apps.get_model("blog_types", "Category")
    if not Category.objects.filter(section__isnull=True).exists() and Section.objects.exists():
        return
    section = Section.objects.filter(name="판매 수익 (커넥트)").first() or Section.objects.create(
        name="판매 수익 (커넥트)", note=NOTE, order=1)
    Category.objects.filter(section__isnull=True).update(section=section)


class Migration(migrations.Migration):
    dependencies = [("blog_types", "0003_section")]
    operations = [
        migrations.RunPython(forward, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="category",
            name="section",
            field=models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="categories",
                                    to="blog_types.section", verbose_name="대분류"),
        ),
    ]
