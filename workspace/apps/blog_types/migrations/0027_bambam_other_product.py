"""밤밤 › 그 외 = 제품소개 (2026-10-24 사용자: 글감이 없을 수 없다).

'그 외'의 방향이 다른 사이트와 같은 "강한 소재가 있을 때만"이라 기획자가 커스텀 글쓰기에서도 '없음'으로 건너뛰었다.
밤밤의 '그 외'만 방향·독자의 질문을 제품소개로 바꾼다 (이름은 그대로). 지우는 데이터 없음.
"""
from django.db import migrations

DIRECTION = "제품소개: 이미 파는 제품 하나를 무엇·왜·누구에게·가격·장단점으로. 늘 글감이 있다 (비교는 상품 추천)"
QUESTION = "이 제품 뭐고, 나한테 맞을까"


def forward(apps, schema_editor):
    Category = apps.get_model("blog_types", "Category")
    Category.objects.filter(section__name="밤밤", name="그 외", deleted_at__isnull=True).update(
        direction=DIRECTION, question=QUESTION)


class Migration(migrations.Migration):

    dependencies = [
        ("blog_types", "0026_bambam_stock_concept"),
    ]

    operations = [
        migrations.RunPython(forward, migrations.RunPython.noop),
    ]
