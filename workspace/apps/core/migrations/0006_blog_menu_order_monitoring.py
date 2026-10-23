"""블로그·카페 중메뉴 순서 (2026-10-23 사용자): 모니터링 · 글 관리(› 발행예정글 · 게시글 관리 · 카테고리 관리 · 사이트별 템플릿) ·
memorily 티스토리.

0005 와 같다: 관리화면 › 메뉴 권한에서 순서를 저장해 두었을 때만 이 묶음의 순서 값을 새 순서로 맞춘다 (이름·숨김·그룹은 그대로).
"""
from django.db import migrations

ORDERS = [
    ["blog_ops", "posts_view", "memorily_tistory"],
    ["posts_planned", "posts_published", "blog_types", "site_templates"],
]


def apply(apps, schema_editor):
    MenuSetting = apps.get_model("core", "MenuSetting")
    if not MenuSetting.objects.exists():
        return
    for keys in ORDERS:
        for i, key in enumerate(keys, start=1):
            MenuSetting.objects.update_or_create(key=key, defaults={"order": i * 10})


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0005_blog_menu_order"),
    ]

    operations = [
        migrations.RunPython(apply, migrations.RunPython.noop),
    ]
