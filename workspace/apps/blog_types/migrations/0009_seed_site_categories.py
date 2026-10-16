"""사이트 카테고리 처음 값: 2026-10-16 각 블로그 화면에서 직접 확인한 실제 카테고리 이름 (메뉴 순서 그대로).

- memorily (jinbaam.tistory.com): 9개, 하위 카테고리 없음. 'Vue.js, Node.js' 는 메뉴에 'VUE / NODE' 로 보인다.
- black_lukey (네이버): 처음 만들어진 두 개뿐, 글 0편.
- 눈잎·밤밤: 카테고리와 글이 아직 없다. 워드프레스는 주소가 없다.

사이트 카테고리가 이미 있으면 넣지 않는다 (화면에서 고친 값을 덮지 않게).
"""
from django.db import migrations

SITES = {
    "memorily": [
        ("Vue.js, Node.js", "메뉴 표시: VUE / NODE"),
        ("Java", ""),
        ("Database", ""),
        ("Android Studio", ""),
        ("Make", ""),
        ("공모전 및 프로젝트", ""),
        ("자격증", ""),
        ("일상생활", ""),
        ("기타", ""),
    ],
    "black_lukey": [
        ("낙서장", "네이버 기본 카테고리"),
        ("videolog", "네이버 기본 동영상 카테고리"),
    ],
}


def seed(apps, schema_editor):
    Blog = apps.get_model("blog_rules", "Blog")
    SiteCategory = apps.get_model("blog_types", "SiteCategory")
    if SiteCategory.objects.exists():
        return
    for name, cats in SITES.items():
        blog = Blog.objects.filter(name=name, deleted_at__isnull=True).first()
        if blog is None:
            continue
        for order, (cat, note) in enumerate(cats, start=1):
            SiteCategory.objects.create(blog=blog, name=cat, note=note, order=order)


class Migration(migrations.Migration):
    dependencies = [("blog_types", "0008_site_category"), ("blog_rules", "0007_checks_by_site")]
    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
