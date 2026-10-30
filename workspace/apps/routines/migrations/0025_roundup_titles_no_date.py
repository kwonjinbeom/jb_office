"""memorily 총정리 제목에서 기준일 빼기 (2026-10-31 사용자: "10월 31일 기준 이런 건 빼").

0024 가 고정 주제 지침 · 갈래 컨셉에 넣은 제목 줄의 '상세(… · 기준일)'와 예시의 '(10월 31일 기준)'을 고친다.
기준일은 본문 표 아래 한 줄에만 둔다. 0024 의 글 그대로일 때만 바꾼다. 지우는 데이터 없음.
"""
from django.db import migrations

NAMES = ("무료 AI 툴", "이달의 AI", "IT 할인")
OLD = "이번 편과 상세(검색어 · 숫자 · 기준일)만 바꾼다."
NEW = "이번 편과 상세(검색어 · 숫자)만 바꾼다. 제목에 기준일(`(10월 31일 기준)` 같은 것)은 넣지 않는다 — 본문 표 아래 한 줄로."
OLD_EXAMPLE = " (10월 31일 기준)`"


def fix(text):
    return text.replace(OLD, NEW).replace(OLD_EXAMPLE, "`")


def forward(apps, schema_editor):
    FixedTopic = apps.get_model("routines", "FixedTopic")
    SiteCategory = apps.get_model("blog_types", "SiteCategory")
    for topic in FixedTopic.objects.filter(name__in=NAMES, deleted_at__isnull=True):
        if fix(topic.note) != topic.note:
            topic.note = fix(topic.note)
            topic.save(update_fields=["note"])
    for cat in SiteCategory.objects.filter(blog__name="memorily", name__in=NAMES, deleted_at__isnull=True):
        if fix(cat.concept) != cat.concept:
            cat.concept = fix(cat.concept)
            cat.save(update_fields=["concept"])


class Migration(migrations.Migration):
    dependencies = [("routines", "0024_roundup_titles")]
    operations = [migrations.RunPython(forward, migrations.RunPython.noop)]
