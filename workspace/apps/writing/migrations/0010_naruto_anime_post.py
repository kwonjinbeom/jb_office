"""T84 나루토 환산기 글을 발행예정글에 넣고 memorily › 애니 에 매핑, 변환 완료로 둔다 (2026-10-21 사용자).

이 글은 처음부터 티스토리용으로 썼으므로 변환본 = 원고 그대로다. 서버 DB 는 에이전트가 직접 못 만지므로 migration 으로 넣는다.
사용자가 만든 memorily 의 '애니' 카테고리가 있는 DB(서버)에서만 한다 — 없으면(시험·PC DB) 아무것도 안 한다.
같은 제목 글이 있으면 그 글을 옮긴다 (원고 자동 가져오기가 먼저 임시글로 넣었어도). 지우는 데이터는 없다.
"""
from django.conf import settings
from django.db import migrations
from django.utils import timezone

DRAFT = ("콘텐츠", "블로그_카페", "포스팅자동화", "원고", "T84_나루토환산기", "원고.md")


def forward(apps, schema_editor):
    from apps.writing.drafts import parse

    Blog = apps.get_model("blog_rules", "Blog")
    SiteCategory = apps.get_model("blog_types", "SiteCategory")
    Placement = apps.get_model("blog_types", "Placement")
    Category = apps.get_model("blog_types", "Category")
    Post = apps.get_model("writing", "Post")

    blog = Blog.objects.filter(name="memorily", deleted_at__isnull=True).first()
    cat = blog and SiteCategory.objects.filter(blog=blog, name__startswith="애니", deleted_at__isnull=True).order_by("pk").first()
    path = settings.REPO_ROOT.joinpath(*DRAFT)
    if not cat or not path.is_file():
        return
    draft = parse(path.read_text(encoding="utf-8"), DRAFT[-2])
    if draft is None:
        return

    post = Post.objects.filter(title=draft.title).order_by("pk").first() or Post(title=draft.title)
    post.stage, post.review_status, post.write_status = "post", "done", "done"
    post.body, post.tags, post.summary, post.target = draft.body, draft.tags, draft.summary, "memorily"
    post.deleted_at = None
    post.bt_category = Category.objects.filter(name="콘텐츠·엔터", deleted_at__isnull=True).first()
    post.save()

    pl = Placement.objects.filter(site_category=cat, tistory_post=post).first() or Placement(site_category=cat, tistory_post=post)
    pl.deleted_at = None
    pl.converted_title, pl.converted_body, pl.converted_tags = draft.title, draft.body, draft.tags
    pl.converted_check = "처음부터 memorily › 애니 용으로 쓴 글이라 변환 없이 원고 그대로. 회차·화수 출처는 원고 '확인한 사실'."
    pl.convert_status, pl.converted_at = "done", timezone.now()
    pl.save()


class Migration(migrations.Migration):

    dependencies = [
        ("writing", "0009_post_target_site"),
        ("blog_types", "0016_placement_converted_check"),
        ("blog_rules", "0008_site_day"),
    ]

    operations = [migrations.RunPython(forward, migrations.RunPython.noop)]
