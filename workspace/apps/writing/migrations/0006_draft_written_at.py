"""글 관리에 저절로 들어온 원고(T26~)의 '만든 날'을 원고를 쓴 날로 (2026-10-16 사용자).

처음에는 가져온 시각으로 찍혀, 16일 밤에 쓴 원고 11편이 17일 글이 됐다. 원고.md 가 git 에 처음 올라온 시각으로 고친다.
지우는 데이터는 없다. 같은 제목의 원고가 없거나 이미 그보다 이른 날이면 그대로 둔다.
"""
from django.db import migrations


def forward(apps, schema_editor):
    from apps.writing import drafts

    Post = apps.get_model("writing", "Post")
    for d in drafts.list_drafts():
        number = d.code[1:]
        if not (number.isdigit() and int(number) >= 26):  # writing.views.AUTO_IMPORT_FROM
            continue
        written = drafts.written_at(d)
        Post.objects.filter(title=d.title, created_at__gt=written).update(created_at=written)


class Migration(migrations.Migration):

    dependencies = [("writing", "0005_post_bt_category_post_bt_sub_post_bt_type")]

    operations = [migrations.RunPython(forward, migrations.RunPython.noop)]
