"""
'내 아이디어'를 비운다 (2026-10-14 사용자 지시).

지금까지 들어 있던 것은 시장조사 문서에서 한꺼번에 넣은 후보(seed_ideas)이고, 사용자가 직접 담은 것은 없다.
이제 '내 아이디어'에는 일일 아이디어에서 직접 담은 것만 둔다.
아이디어에 달린 단계·작업 로그는 함께 지워지고, 할 일·증거 링크·콘텐츠·논의는 남되 아이디어 연결만 풀린다.
되돌릴 수 없다. 이 migration 은 DB 마다 한 번만 실행된다.
"""
from django.db import migrations


def clear(apps, schema_editor):
    apps.get_model("ideas", "Idea").objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [("ideas", "0002_stage_idealog")]
    operations = [migrations.RunPython(clear, migrations.RunPython.noop)]
