"""글 관리 = 접고 펴기만 하는 중메뉴(posts_hub), 그 아래 첫 소메뉴 '임시·검토글'(posts_view, 예전 글 관리 화면) (2026-10-23 사용자).

0005·0006 과 같다: 관리화면 › 메뉴 권한에서 순서를 저장해 두었을 때만 이 묶음의 순서 값을 새 순서로 맞춘다.
예전 posts_view 에 이름을 '글 관리' 로 저장해 두었다면 그 이름은 비운다 (이제 그 줄은 '임시·검토글'). 지우는 데이터 없음.
"""
from django.db import migrations

ORDERS = [
    ["blog_ops", "posts_hub", "memorily_tistory"],
    ["posts_view", "posts_planned", "posts_published", "blog_types", "site_templates"],
]


def apply(apps, schema_editor):
    MenuSetting = apps.get_model("core", "MenuSetting")
    if not MenuSetting.objects.exists():
        return
    MenuSetting.objects.filter(key="posts_view", title="글 관리").update(title="")
    for keys in ORDERS:
        for i, key in enumerate(keys, start=1):
            MenuSetting.objects.update_or_create(key=key, defaults={"order": i * 10})


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0006_blog_menu_order_monitoring"),
    ]

    operations = [
        migrations.RunPython(apply, migrations.RunPython.noop),
    ]
