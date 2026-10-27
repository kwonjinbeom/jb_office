"""컨셉 정리에 따른 데이터 정리 (2026-10-27 사용자가 고른 대로).

휴지통으로 (7일 동안 복원할 수 있다):
- 사이트 체크 7줄: 지금과 안 맞는 6줄 (memorily '눈잎과 같은 카카오 계정: 둘 합쳐 하루 3편 이하' · '관심분야(애니 등) 카테고리는 보류',
  눈잎 'memorily와 합쳐 하루 3편 이하' · '애드센스 승인 확인 → 하루 2편으로', black_lukey 'RSS 공개 설정 확인 (지금 공개 글 0편)',
  밤밤 '하루 편수 정하기') + 세일 소재를 빼면서 black_lukey '올영·무신사 행사는 조회용 소재 (링크 없음)'.
- 컨셉도 글도 없는 사이트 카테고리 12개: memorily 옛 개발 카테고리 9개 · black_lukey 세일 이벤트 · 일상 · 밤밤 일상.
  실제 블로그의 카테고리는 그대로다. 넣은 글이 있으면 지우지 않는다.
- 글 분류 black_lukey › 세일 이벤트 (소재). 그 분류의 글이 있으면 지우지 않는다. black_lukey 사이트 컨셉에서 '인기 세일'을 뺀다.
옮기기: '독감 무료접종 일정, 올해는 왜 빨라졌을까?' 글을 눈잎 › 청년·신혼 정책 → 생활 (사이트 카테고리 · 글 분류 둘 다).
"""
from django.db import migrations
from django.utils import timezone

CHECKS = {
    "memorily": ["눈잎과 같은 카카오 계정: 둘 합쳐 하루 3편 이하", "관심분야(애니 등) 카테고리는 보류"],
    "눈잎": ["memorily와 합쳐 하루 3편 이하", "애드센스 승인 확인 → 하루 2편으로"],
    "black_lukey": ["RSS 공개 설정 확인 (지금 공개 글 0편)", "올영·무신사 행사는 조회용 소재 (링크 없음)"],
    "밤밤": ["하루 편수 정하기"],
}
EMPTY_CATS = {
    "memorily": ["Vue.js, Node.js", "Java", "Database", "Android Studio", "Make", "공모전 및 프로젝트", "자격증", "일상생활", "기타"],
    "black_lukey": ["세일 이벤트", "일상"],
    "밤밤": ["일상"],
}
FLU = "독감 무료접종 일정, 올해는 왜 빨라졌을까?"


def _trash(apps, label, key, title, section, members, now):
    """휴지통 한 묶음 (0028 과 같다): 공통 휴지통에 이름·위치·PK 목록을 남기고 행마다 deleted_at."""
    TrashEntry = apps.get_model("core", "TrashEntry")
    TrashEntry.objects.filter(model_label=label, object_key=str(key)).delete()
    TrashEntry.objects.create(model_label=label, object_key=str(key), title=title[:200], section=section,
                              deleted_at=now, members=members)
    for member, ids in members.items():
        app_label, model = member.split(".")
        apps.get_model(app_label, model).objects.filter(pk__in=ids, deleted_at__isnull=True).update(deleted_at=now)


def forward(apps, schema_editor):
    now = timezone.now()
    Blog = apps.get_model("blog_rules", "Blog")
    Rule = apps.get_model("blog_rules", "Rule")
    SiteCategory = apps.get_model("blog_types", "SiteCategory")
    Placement = apps.get_model("blog_types", "Placement")
    Category = apps.get_model("blog_types", "Category")
    PostType = apps.get_model("blog_types", "PostType")
    SubType = apps.get_model("blog_types", "SubType")
    TistoryPost = apps.get_model("writing", "Post")
    NaverPost = apps.get_model("naver_writing", "Post")
    FixedTopic = apps.get_model("routines", "FixedTopic")

    for site, bodies in CHECKS.items():
        for rule in Rule.objects.filter(blog__name=site, body__in=bodies, deleted_at__isnull=True):
            _trash(apps, "blog_rules.rule", rule.pk, rule.body, "운영 · 체크", {"blog_rules.rule": [rule.pk]}, now)

    for site, names in EMPTY_CATS.items():
        for cat in SiteCategory.objects.filter(blog__name=site, name__in=names, parent=None, deleted_at__isnull=True):
            ids = [cat.pk, *SiteCategory.objects.filter(parent=cat, deleted_at__isnull=True).values_list("pk", flat=True)]
            if cat.concept.strip() or Placement.objects.filter(site_category__in=ids, deleted_at__isnull=True).exists():
                continue
            _trash(apps, "blog_types.sitecategory", cat.pk, f"{site} › {cat.name}", "카테고리 관리 · 사이트 카테고리",
                   {"blog_types.sitecategory": ids}, now)

    for cat in Category.objects.filter(section__name="black_lukey", name="세일 이벤트", deleted_at__isnull=True):
        used = (TistoryPost.objects.filter(bt_category=cat, deleted_at__isnull=True).exists()
                or NaverPost.objects.filter(bt_category=cat, deleted_at__isnull=True).exists()
                or FixedTopic.objects.filter(category=cat, deleted_at__isnull=True).exists())
        if used:
            continue
        types = list(PostType.objects.filter(category=cat, deleted_at__isnull=True).values_list("pk", flat=True))
        subs = list(SubType.objects.filter(post_type__in=types, deleted_at__isnull=True).values_list("pk", flat=True))
        members = {"blog_types.category": [cat.pk]}
        if types:
            members["blog_types.posttype"] = types
        if subs:
            members["blog_types.subtype"] = subs
        _trash(apps, "blog_types.category", cat.pk, f"black_lukey › {cat.name}", "카테고리 관리 · 카테고리", members, now)
    for blog in Blog.objects.filter(name="black_lukey", deleted_at__isnull=True):
        if " · 인기 세일" in blog.content:
            blog.content = blog.content.replace(" · 인기 세일", "", 1)
            blog.save(update_fields=["content"])

    life = SiteCategory.objects.filter(blog__name="눈잎", name="생활", parent=None, deleted_at__isnull=True).first()
    youth = SiteCategory.objects.filter(blog__name="눈잎", name="청년·신혼 정책", parent=None, deleted_at__isnull=True).first()
    life_class = Category.objects.filter(section__name="눈잎", name="생활", deleted_at__isnull=True).first()
    if life and youth:
        for post in TistoryPost.objects.filter(title__startswith=FLU, deleted_at__isnull=True):
            Placement.objects.filter(tistory_post=post, site_category=youth, deleted_at__isnull=True).update(site_category=life)
            if life_class and post.bt_category_id != life_class.pk:
                post.bt_category, post.bt_type, post.bt_sub = life_class, None, None
                post.save(update_fields=["bt_category", "bt_type", "bt_sub"])


class Migration(migrations.Migration):
    dependencies = [
        ("blog_types", "0041_photo_counts"),
        ("blog_rules", "0009_site_targets"),
        ("core", "0007_posts_hub_menu"),
        ("writing", "0026_trash_nunip_kospi"),
        ("naver_writing", "0008_post_planned_on"),
        ("routines", "0021_topic_daily"),
    ]
    operations = [migrations.RunPython(forward, migrations.RunPython.noop)]
