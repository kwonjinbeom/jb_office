"""black_lukey › 세일 이벤트를 되살린다 (2026-10-31 사용자: "글쓰기 · 템플릿 등 글쓰기에 관련된 카테고리 구조에서 확실히 살려 줘.
글은 안 살려도 된다. 노트북 구매 타이밍 같은 건 취지와 너무 다르다 — 브랜드 세일을 하고, 없으면 안 써도 된다").

10-27 0042 가 휴지통으로 보낸 것을 꺼낸다 (휴지통 항목도 지운다 — 7일 뒤 영구 삭제되지 않게). 이미 영구 삭제됐으면 새로 만든다.
1. 글 분류 black_lukey › 세일 이벤트 (소재). 방향을 '브랜드 정기 세일·블프 기획전'으로 좁힌다.
2. 사이트 카테고리 black_lukey › 세일 이벤트 + 글 모양 컨셉 (출시의 짜임을 세일에 맞게). 견본은 site_templates.design_cats SALE_EVENT.
3. 사이트 체크 '올영·무신사 행사는 조회용 소재 (링크 없음)'. 사이트 컨셉에 ' · 인기 세일'.
같은 글이 작가 파일(일일루틴/프롬프트/writing_site_black_lukey.md)에도 있다 — 고칠 때 둘 다. 지우는 데이터 없음.
"""
from django.db import migrations

NAME = "세일 이벤트"
DIRECTION = "올영·무신사·유니클로 등 브랜드 정기 세일·블프 기획전의 기간·혜택·살 만한 것 (공식 공지가 있을 때만)"
QUESTION = "이번 세일 언제 하고 뭘 사면 좋지"
CHECK = "올영·무신사 행사는 조회용 소재 (링크 없음)"
CONTENT = " · 인기 세일"
CONCEPT = """세일 이벤트: 올리브영(올영세일·올영데이) · 무신사(블랙프라이데이·무진장) · 유니클로(감사제) · 29CM · 쿠팡 · 코리아세일페스타처럼
브랜드·쇼핑몰이 공식 공지한 정기 세일·블프 기획전 한 회차를 한 편에 (시작 7~10일 전 ~ 진행 첫 주). 공식 공지가 없으면 쓰지 않는다.
다루지 않는 것: 품목 하나의 구매 타이밍·가격 추이(노트북·패딩 언제 살까) · IT 기기 할인 행사(memorily › IT 할인).
글 모양 (black_lukey › 출시의 짜임을 세일에 맞게: 결론 → 일정 표 → 알려진 것 → 살 만한 것 → 공식 공지):
- 순서: 맨 위 인용(결론 2~3문장: 언제부터 언제까지 · 가장 큰 혜택 한 줄) → 한눈에 표(행사 · 기간 · 할인 · 쿠폰·적립 · 대상) → 지난 회차 표(회차 · 기간 · 최대 할인, 확인된 것만) → 혜택마다 소제목 → 이번에 살 만한 것 → 놓치기 쉬운 것 → 공식 공지 보는 곳
- 행사 카드 `::: 제품 | 행사 이름` (카드 종류는 장소·맛집·작품·제품뿐 — IT 할인과 같이 제품): 📅 기간 · ⏰ 시작 시각 · 💸 할인 · 🎟️ 쿠폰·적립 · 👤 대상(회원 등급·앱 전용) · 🔗 공식 공지.
- 이번에 살 만한 것: 그 브랜드 공식 기획전에 오른 것 중 3~5개, 상품마다 사진 1장 · 2~3문장(왜 이번이 싼지 · 누구에게). 써 본 척하지 않는다.
- 놓치기 쉬운 것: 쿠폰 받는 시각 · 등급별 쿠폰 · 앱 전용 · 같이 안 되는 혜택을 짧은 목록으로.
- 기간·할인율·쿠폰은 브랜드 공식 앱 공지·이벤트 페이지로 확인한 것만. 표 아래에 '○월 ○일 공식 공지 기준 · 바뀔 수 있어요' 한 줄.
- 사진: 공식 기획전 배너 · 매장 · 상품 실물 (직접 찍은 것 우선). 링크는 조회용 공식 페이지 — 쇼핑커넥트는 참여 스마트스토어 상품만, 대가 문구는 첫 부분."""


def _undelete(model, qs, TrashEntry, label):
    """휴지통에 있으면 꺼내고 그 휴지통 항목을 지운다. 꺼낸 것(또는 살아 있는 것) 하나를 돌려준다."""
    alive = qs.filter(deleted_at__isnull=True).first()
    if alive:
        return alive
    gone = qs.exclude(deleted_at__isnull=True).order_by("-deleted_at").first()
    if gone is None:
        return None
    TrashEntry.objects.filter(model_label=label, object_key=str(gone.pk)).delete()
    gone.deleted_at = None
    gone.save(update_fields=["deleted_at"])
    return gone


def forward(apps, schema_editor):
    Blog = apps.get_model("blog_rules", "Blog")
    Rule = apps.get_model("blog_rules", "Rule")
    Section = apps.get_model("blog_types", "Section")
    Category = apps.get_model("blog_types", "Category")
    SiteCategory = apps.get_model("blog_types", "SiteCategory")
    TrashEntry = apps.get_model("core", "TrashEntry")

    section = Section.objects.filter(name="black_lukey", deleted_at__isnull=True).first()
    if section:
        cat = _undelete(Category, Category.objects.filter(section=section, name=NAME), TrashEntry, "blog_types.category")
        if cat is None:
            used = set(Category.objects.filter(section=section, deleted_at__isnull=True).values_list("code", flat=True))
            code = next(c for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ" if c not in used)
            order = max(Category.objects.filter(section=section, deleted_at__isnull=True).values_list("order", flat=True), default=0) + 1
            cat = Category.objects.create(section=section, code=code, name=NAME, order=order)
        # 0042 가 소재와 함께 넣은 옛 타입·하위는 휴지통에 남긴다 (소분류는 두지 않는다)
        cat.direction, cat.question = DIRECTION, QUESTION
        cat.save(update_fields=["direction", "question"])

    blog = Blog.objects.filter(name="black_lukey", deleted_at__isnull=True).first()
    if blog is None:
        return
    site_cat = _undelete(SiteCategory, SiteCategory.objects.filter(blog=blog, parent=None, name=NAME), TrashEntry,
                         "blog_types.sitecategory")
    if site_cat is None:
        order = max(SiteCategory.objects.filter(blog=blog, parent=None, deleted_at__isnull=True)
                    .values_list("order", flat=True), default=0) + 1
        site_cat = SiteCategory.objects.create(blog=blog, name=NAME, order=order)
    if not site_cat.concept.strip():
        site_cat.concept = CONCEPT
        site_cat.save(update_fields=["concept"])

    rule = _undelete(Rule, Rule.objects.filter(blog=blog, body=CHECK), TrashEntry, "blog_rules.rule")
    if rule is None:
        order = max(Rule.objects.filter(blog=blog, deleted_at__isnull=True).values_list("order", flat=True), default=0) + 1
        Rule.objects.create(blog=blog, body=CHECK, order=order)

    if CONTENT.strip(" ·") not in blog.content:
        anchor = "신제품·영화 출시"
        blog.content = (blog.content.replace(anchor, anchor + CONTENT, 1) if anchor in blog.content
                        else blog.content.rstrip() + CONTENT)[:200]
        blog.save(update_fields=["content"])


class Migration(migrations.Migration):
    dependencies = [
        ("blog_types", "0052_memorily_roundups"),
        ("blog_rules", "0009_site_targets"),
        ("core", "0007_posts_hub_menu"),
    ]
    operations = [migrations.RunPython(forward, migrations.RunPython.noop)]
