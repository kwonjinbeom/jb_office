"""2026-10-16 사용자: memorily = https://jinbaam.tistory.com/, 눈잎 = https://nunip.tistory.com/
주소가 비어 있을 때만 넣는다 (화면에서 넣은 값은 그대로)."""
from django.db import migrations

ADDRESSES = {"memorily": "https://jinbaam.tistory.com/", "눈잎": "https://nunip.tistory.com/"}


def forward(apps, schema_editor):
    Blog = apps.get_model("blog_rules", "Blog")
    for name, address in ADDRESSES.items():
        Blog.objects.filter(name=name, address="").update(address=address)


class Migration(migrations.Migration):
    dependencies = [("blog_rules", "0004_bambam_quality")]
    operations = [migrations.RunPython(forward, migrations.RunPython.noop)]
