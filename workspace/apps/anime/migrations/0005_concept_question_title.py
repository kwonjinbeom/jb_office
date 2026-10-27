"""memorily › 애니 카테고리 컨셉의 제목 규칙을 검색 질문형으로 (2026-10-27 사용자: 제목 규칙이 바뀌었다면서 또 옛날처럼 됐다).

10-26 에 글 10편의 제목은 질문형으로 바꿨지만 이 컨셉 · 글쓰기 안내문(anime.run) 은 옛 꼴 그대로여서 주술회전 · 은혼이 옛 제목으로 나왔다.
0003 이 넣은 말이 그대로 있을 때만 바꾼다. 지우는 데이터 없음.
"""
from django.db import migrations

PAIRS = [
    ("제목은 `<작품> 회차정리 애니만화 환산기 명장면 등 모음`.",
     "제목은 검색 질문형 (2026-10-26): `<작품> <자동완성에서 가장 많이 묻는 질문>? 화수 환산기·<보는 순서 · 극장판 순서 · 오리지널 회차 중 1~2개>` "
     "— 예 `블리치 천년혈전은 만화 몇 화부터? 화수 환산기와 오리지널 스킵 회차`. '회차정리 애니만화 환산기 명장면 등 모음' 같은 나열 제목은 쓰지 않는다."),
    ("- 맨 위 요약 없이 바로 '화수 환산기'로 시작한다.",
     "- 맨 위 요약 없이, 제목 아래 한 문장 `<작품> 애니 몇 화가 만화 몇 화·몇 권인지, 아래 환산기에 화수를 넣으면 바로 나와요.` 다음 바로 '화수 환산기'."),
]


def forward(apps, schema_editor):
    SiteCategory = apps.get_model("blog_types", "SiteCategory")
    for old, new in PAIRS:
        for cat in SiteCategory.objects.filter(concept__contains=old):
            cat.concept = cat.concept.replace(old, new)
            cat.save(update_fields=["concept"])


class Migration(migrations.Migration):

    dependencies = [
        ("anime", "0004_concept_calc_data_outside_skin"),
    ]

    operations = [migrations.RunPython(forward, migrations.RunPython.noop)]
