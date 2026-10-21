"""원고.md 를 서버 DB 에 바로 넣는 migration 도우미 (2026-10-21, 애니 총정리 글).

서버 DB 는 에이전트가 직접 못 만지므로 migration 이 원고를 읽어 넣는다: 발행예정글 + 사이트 카테고리 매핑 + 변환 완료
(처음부터 그 사이트용으로 쓴 글이라 변환본 = 원고). writing 0010(나루토)의 일반판이다.
- 같은 제목 글이 있으면 그 글을 고친다 (원고 자동 가져오기가 먼저 임시글로 넣었어도).
- 사이트 카테고리가 없는 DB(시험·PC)에서는 아무것도 안 한다. 원고 파일과 같은 커밋에 넣는다 (먼저 올라가면 빈손으로 돈다).
"""
from django.conf import settings
from django.utils import timezone

DRAFTS = ("콘텐츠", "블로그_카페", "포스팅자동화", "원고")


def place(apps, folder, site="memorily", category_prefix="애니", classification="콘텐츠·엔터"):
    """원고 폴더(T85_블리치환산기 등) 하나를 넣는다. 넣었으면 True."""
    from apps.writing.drafts import parse

    Blog = apps.get_model("blog_rules", "Blog")
    SiteCategory = apps.get_model("blog_types", "SiteCategory")
    Placement = apps.get_model("blog_types", "Placement")
    Category = apps.get_model("blog_types", "Category")
    Post = apps.get_model("writing", "Post")

    blog = Blog.objects.filter(name=site, deleted_at__isnull=True).first()
    cat = blog and SiteCategory.objects.filter(blog=blog, name__startswith=category_prefix,
                                               deleted_at__isnull=True).order_by("pk").first()
    path = settings.REPO_ROOT.joinpath(*DRAFTS, folder, "원고.md")
    if not cat or not path.is_file():
        return False
    draft = parse(path.read_text(encoding="utf-8"), folder)
    if draft is None:
        return False

    post = Post.objects.filter(title=draft.title).order_by("pk").first() or Post(title=draft.title)
    post.stage, post.review_status, post.write_status = "post", "done", "done"
    post.body, post.tags, post.summary, post.target = draft.body, draft.tags, draft.summary, site
    post.deleted_at = None
    post.bt_category = Category.objects.filter(name=classification, deleted_at__isnull=True).first()
    post.save()

    pl = Placement.objects.filter(site_category=cat, tistory_post=post).first() or Placement(site_category=cat, tistory_post=post)
    pl.deleted_at = None
    pl.converted_title, pl.converted_body, pl.converted_tags = draft.title, draft.body, draft.tags
    pl.converted_check = f"처음부터 {site} › {cat.name} 용으로 쓴 글이라 변환 없이 원고 그대로. 회차·화수 출처는 원고 '확인한 사실'."
    pl.convert_status, pl.converted_at = "done", timezone.now()
    pl.save()
    return True
