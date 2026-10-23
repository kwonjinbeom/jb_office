"""memorily › AI (2026-10-23 사용자): 카테고리 관리의 글 분류에 memorily · AI, 사이트 카테고리에도 AI, AI 소식은 발행 때 여기로.

1. 글 분류: 대분류 'memorily' + 소재 'AI'. memorily 는 글쓰기 루틴을 끈 사이트라 일일 분량에는 들지 않는다
   (routines.views.default_picks). AI 소식은 고정 주제로 쓰고, 그 소재를 여기로 둔다 (원고의 '분류:' 줄 → 글 분류).
2. 사이트 카테고리 memorily › AI: 컨셉에 AI 글 모양(도구마다 사진 1장 · 정리한 가공이미지 · 소제목 빨간 막대), 소제목 빨간 막대 켬.
3. 지금 있는 AI 소식 글: 글 분류를 memorily › AI 로. 아직 발행하지 않은 글의 memorily 넣은 곳은 AI 로 옮긴다 (발행한 글은 그대로).
지우는 데이터 없음.
"""
from django.db import migrations, models

AI_CONCEPT = """AI 소식: 핵심 AI 도구의 근황을 도구마다 짧게. 원문의 말·소제목('도구 — 요약 설명')은 그대로 둔다.
글 모양 (변환이 채운다, 2026-10-23 사용자):
- 사진: 도구(## 소제목)마다 1장씩, 그 소제목 바로 아래. 그 도구와 관련된 장면이면 된다 — 꼭 똑같지 않아도 된다 (잠금 채팅 → 휴대폰 잠금 화면, 지도 기억 → 지도 앱, 코딩 모델 → 노트북 코드 화면, 보안 → 서버실). 무료 사진(Unsplash·Pexels·Pixabay)을 먼저, 회사 뉴스룸이 언론 사용을 허락한 공식 이미지는 출처를 달아 쓴다. 이 카테고리는 '사진 1장' 기준보다 이것이 먼저다.
- 가공이미지: 몇 장 (보통 2~3장). 맨 위 인용 다음에 '오늘의 AI 소식 한눈에'(도구 · 바뀐 것 한 줄 · 누구에게) 정리 그림 1장, 그리고 요금제·대상·숫자·순서처럼 정리하면 빨리 읽히는 항목에 1~2장. 흰 바탕 · Pretendard · 포인트 컬러 빨강 #e03131.
- 소제목: 크기·말은 그대로. 앞의 빨간 세로 막대는 붙여넣는 HTML 이 단다 — 변환본에 꾸밈을 넣지 않는다."""

SECTION_NOTE = "직접 쓰는 글 (애니) · AI 소식 (커스텀 고정 주제) — 글쓰기 루틴을 끈 사이트라 일일 분량에는 들지 않는다"


def forward(apps, schema_editor):
    Blog = apps.get_model("blog_rules", "Blog")
    Section = apps.get_model("blog_types", "Section")
    Category = apps.get_model("blog_types", "Category")
    SiteCategory = apps.get_model("blog_types", "SiteCategory")
    Placement = apps.get_model("blog_types", "Placement")
    FixedTopic = apps.get_model("routines", "FixedTopic")

    section = Section.objects.filter(name="memorily", deleted_at__isnull=True).first()
    if section is None:
        start = max(Section.objects.filter(deleted_at__isnull=True).values_list("order", flat=True), default=0) + 1
        section = Section.objects.create(name="memorily", note=SECTION_NOTE, order=start)
    cat = Category.objects.filter(section=section, name="AI", deleted_at__isnull=True).first()
    if cat is None:
        cat = Category.objects.create(
            section=section, code="A", name="AI", order=1,
            direction="새로 뜨는 AI와 많이 쓰는 AI의 의미 있는 업데이트를 한 편에 모아, 도구마다 짧게",
            question="요즘 AI 뭐가 새로 나왔고 뭐가 바뀌었지")
    FixedTopic.objects.filter(name="AI 소식", deleted_at__isnull=True).update(category=cat, site="memorily")

    blog = Blog.objects.filter(name="memorily", deleted_at__isnull=True).first()
    if blog is None:
        return
    site_cat = SiteCategory.objects.filter(blog=blog, parent__isnull=True, name="AI", deleted_at__isnull=True).first()
    if site_cat is None:
        start = max(SiteCategory.objects.filter(blog=blog, parent__isnull=True, deleted_at__isnull=True)
                    .values_list("order", flat=True), default=0) + 1
        site_cat = SiteCategory.objects.create(blog=blog, name="AI", order=start)
    site_cat.concept = site_cat.concept.strip() or AI_CONCEPT
    site_cat.heading_bar = True
    site_cat.save()

    for app, field in (("writing", "tistory_post"), ("naver_writing", "naver_post")):
        Post = apps.get_model(app, "Post")
        posts = Post.objects.filter(deleted_at__isnull=True, title__contains="AI 소식")
        posts.update(bt_category=cat, bt_type=None, bt_sub=None)
        (Placement.objects.filter(**{f"{field}__in": posts}, status="unsaved", deleted_at__isnull=True,
                                  site_category__blog=blog).exclude(site_category=site_cat)
         .update(site_category=site_cat))


class Migration(migrations.Migration):

    dependencies = [
        ("blog_types", "0020_site_links"),
        ("blog_rules", "0009_site_targets"),
        ("routines", "0021_topic_daily"),
        ("writing", "0021_mha_wording"),
        ("naver_writing", "0008_post_planned_on"),
    ]

    operations = [
        migrations.AddField(
            model_name="sitecategory",
            name="heading_bar",
            field=models.BooleanField(default=False, help_text="붙여넣는 HTML 의 소제목(##) 앞에 빨간 세로 막대를 단다 (하위 카테고리도 따른다)",
                                      verbose_name="소제목 빨간 막대"),
        ),
        migrations.RunPython(forward, migrations.RunPython.noop),
    ]
