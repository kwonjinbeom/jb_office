"""글쓰기 루틴의 화면을 글 관리(posts:view)로 (2026-10-22 사용자: 예전 글 관리 posts:index 를 메뉴에서 뺐다).
루틴 수정 폼의 '화면' 고르기는 메뉴에 있는 화면만 받으므로, 예전 주소로 남아 있으면 저장이 안 된다. 지우는 데이터 없음."""
from django.db import migrations

OLD = ("posts:index", "writing:list", "naver_writing:list")


def forward(apps, schema_editor):
    apps.get_model("routines", "Routine").objects.filter(url_name__in=OLD).update(url_name="posts:view")


class Migration(migrations.Migration):

    dependencies = [
        ("routines", "0013_merge_regions"),
    ]

    operations = [migrations.RunPython(forward, migrations.RunPython.noop)]
