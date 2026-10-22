"""눈잎 사이트 카테고리 = 티스토리 관리 화면 그대로 (2026-10-22 사용자 캡처), 순서도 같게.

청년·신혼 정책 · 주택 공고 · 공모주 · 해외 여행 · 일본 여행 · 일상. 메모에 티스토리 주제 연결을 적는다.
이름이 같은 카테고리가 있으면 그것을 쓰고(넣은 글 유지), 없으면 만든다. 목록에 없는 눈잎 카테고리는
넣은 글이 없으면 휴지통으로(7일 안 복원), 넣은 글이 있으면 지우지 않고 맨 뒤로 보낸다.
글 분류 '눈잎 > 소재'도 같은 순서로 (엔화·환율은 일본 여행 다음, 그 외는 끝).
"""
from django.db import migrations
from django.utils import timezone

SITE = [
    ("청년·신혼 정책", "건강", "청년·신혼부부가 받을 수 있는 지원 — 대상·금액·신청 기간·마감을 표로"),
    ("주택 공고", "생활정보", "행복주택·청년주택·청약 모집공고 — 자격·소득 기준·접수일을 표로"),
    ("공모주", "경제", "공모주 청약·환불·상장 일정과 종목별 핵심 숫자"),
    ("해외 여행", "해외여행", "일본 외 해외 여행의 입국 규정·항공·환율·시즌 알짜 정보"),
    ("일본 여행", "해외여행", "일본 여행의 제도·항공·패스·면세·엔화·축제 일정 알짜 정보"),
    ("일상", "일상다반사", "사용자가 직접 쓰는 일상 글"),
]
CLASS_ORDER = ["청년·신혼 정책", "주택 공고", "공모주", "해외 여행", "일본 여행", "엔화·환율", "그 외"]


def forward(apps, schema_editor):
    Blog = apps.get_model("blog_rules", "Blog")
    SiteCategory = apps.get_model("blog_types", "SiteCategory")
    Placement = apps.get_model("blog_types", "Placement")
    Category = apps.get_model("blog_types", "Category")
    TrashEntry = apps.get_model("core", "TrashEntry")
    now = timezone.now()

    blog = Blog.objects.filter(name="눈잎", deleted_at__isnull=True).first()
    if blog is not None:
        live = list(SiteCategory.objects.filter(blog=blog, parent=None, deleted_at__isnull=True).order_by("order", "pk"))
        by_name = {c.name: c for c in live}
        wanted = set()
        for i, (name, topic, concept) in enumerate(SITE, start=1):
            cat = by_name.get(name) or SiteCategory.objects.create(blog=blog, name=name)
            cat.order = i
            cat.note = cat.note or f"티스토리 주제: {topic}"
            cat.concept = cat.concept or concept
            cat.save(update_fields=["order", "note", "concept"])
            wanted.add(cat.pk)
        extra = [c for c in live if c.pk not in wanted]
        for n, cat in enumerate(extra, start=len(SITE) + 1):
            family = [cat.pk] + list(SiteCategory.objects.filter(parent=cat, deleted_at__isnull=True).values_list("pk", flat=True))
            if Placement.objects.filter(site_category__in=family, deleted_at__isnull=True).exists():
                SiteCategory.objects.filter(pk=cat.pk).update(order=n)  # 넣은 글이 있으면 지우지 않고 뒤로
                continue
            TrashEntry.objects.filter(model_label="blog_types.sitecategory", object_key=str(cat.pk)).delete()
            TrashEntry.objects.create(model_label="blog_types.sitecategory", object_key=str(cat.pk), title=cat.name,
                                      section="카테고리 관리 · 사이트 카테고리", deleted_at=now,
                                      members={"blog_types.sitecategory": family})
            SiteCategory.objects.filter(pk__in=family).update(deleted_at=now)

    for i, name in enumerate(CLASS_ORDER, start=1):
        Category.objects.filter(section__name="눈잎", name=name, deleted_at__isnull=True).update(order=i, code=chr(64 + i))


class Migration(migrations.Migration):
    dependencies = [("blog_types", "0018_site_cleanup"), ("blog_rules", "0009_site_targets"),
                    ("core", "0002_sourceexclusion_trashentry")]
    operations = [migrations.RunPython(forward, migrations.RunPython.noop)]
