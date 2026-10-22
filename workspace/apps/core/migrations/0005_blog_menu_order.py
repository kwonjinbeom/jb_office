"""블로그·카페 중메뉴 순서 (2026-10-23 사용자): 글 관리(› 발행예정글 · 게시글 관리) · 카테고리 관리 · 사이트별 템플릿 · 모니터링 · memorily 티스토리.

관리화면 › 메뉴 권한에서 순서를 저장해 두었으면(MenuSetting) 그 순서가 코드 순서보다 앞선다. 저장한 것이 있을 때만
이 묶음의 순서 값을 새 순서로 맞춘다 (이름·숨김·그룹은 그대로). 저장한 것이 없으면 코드 순서 그대로라 할 일이 없다.
"""
from django.db import migrations

ORDERS = [
    ["posts_view", "blog_types", "site_templates", "blog_ops", "memorily_tistory"],
    ["posts_planned", "posts_published"],
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
        ("core", "0004_menu_groups"),
    ]

    operations = [
        migrations.RunPython(apply, migrations.RunPython.noop),
    ]
