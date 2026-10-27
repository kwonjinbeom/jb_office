"""눈잎에 '생활' 소재 + 사이트 카테고리 '생활' (2026-10-27 사용자: 독감 무료접종 일정 글처럼 정책이라기보다
'알아 두면 좋은 공공 정보'. 주택 공고·공모주·청년·신혼 정책은 늘 있지 않아서 그 사이를 채운다).

1. 글 분류 눈잎에 '생활' (그 외 앞, 기호 다시 매김).
2. 눈잎 사이트 카테고리 '생활' + 글 모양 컨셉 (티스토리 메뉴는 사용자가 만든다).
3. 눈잎 사이트 컨셉에 한 줄.
이름으로 찾아 있는 것만 손댄다. 이미 있으면 건너뛴다. 지우는 데이터 없음.
"""
from django.db import migrations

NAME = "생활"
DIRECTION = "날짜·대상이 정해진 생활 속 공공 제도 — 무료 접종·검진 · 세금·신고 기한 · 지원금·바우처 · 요금·제도 개편 · 면허·민방위"
QUESTION = "이거 나도 해당돼? 언제부터 언제까지, 어디서, 얼마?"
CONCEPT = "\n".join([
    "날짜와 대상이 정해진 생활 속 공공 제도·일정 (2026-10-27 사용자: '독감 무료접종 일정, 올해는 왜 빨라졌을까? 우리 집 나이별로 정리' 같은 글 — "
    "정책이라기보다 알아 두면 좋은 공공 정보).",
    "- 다루는 것: 무료 예방접종·국가건강검진 · 세금·신고 기한(자동차세 연납·종합소득세·연말정산 간소화) · 지원금·바우처(에너지바우처·근로장려금처럼 "
    "청년·신혼에 한정되지 않은 것) · 요금·제도 개편(전기·가스·대중교통·건강보험료) · 생활 행정(면허 갱신·여권·민방위·주민등록).",
    "- 청년·신혼만 대상인 것은 '청년·신혼 정책', 주택 공고는 '주택 공고'로.",
    "",
    "글 모양:",
    "- 제목: 궁금증 + 우리 집 기준. 예) `독감 무료접종 일정, 올해는 왜 빨라졌을까? 우리 집 나이별로 정리`. '총정리'만 붙인 제목은 쓰지 않는다.",
    "- 맨 위 인용 상자: '○월 ○일 ○○(질병관리청·국세청·한전 등) 발표 기준' + 언제부터·누가·무료/얼마 한 줄.",
    "- 대상별 표 하나가 주인공: 나이(출생연도)·소득·가구로 '내 줄'을 바로 찾게 — 대상 | 기간 | 어디서·어떻게 | 비용.",
    "- 올해 달라진 점: 작년 → 올해 한 줄이나 표 (날짜가 당겨짐·대상 확대·금액 변화)와 왜 바뀌었는지 발표 근거.",
    "- 신청·이용: 어디서(앱·사이트·기관) → 준비물 → 순서. 막히면 전화처 한 줄.",
    "- 놓치기 쉬운 것 2~4개 (헷갈리는 기준·잘못 퍼진 말 바로잡기).",
    "- 감상 없이 담백하게, 짧게. 날짜·금액·대상은 부처 보도자료·공식 안내 원문에서만, 글 끝 '참고'에 기관과 날짜.",
    "- 쓸 때: 시작·마감·발표 3~14일 전.",
])
CONTENT = "생활(접종·검진·세금·요금 같은 공공 일정)"


def _renumber(Category, section):
    """기호 A, B, C … 와 순서를 다시 매긴다. '그 외'는 맨 뒤 (0028 과 같다)."""
    cats = sorted(Category.objects.filter(section=section, deleted_at__isnull=True), key=lambda c: (c.name == "그 외", c.order, c.pk))
    for i, c in enumerate(cats):
        Category.objects.filter(pk=c.pk).update(code=chr(65 + i), order=i + 1)


def forward(apps, schema_editor):
    Section = apps.get_model("blog_types", "Section")
    Category = apps.get_model("blog_types", "Category")
    SiteCategory = apps.get_model("blog_types", "SiteCategory")
    Blog = apps.get_model("blog_rules", "Blog")
    nunip = Section.objects.filter(name="눈잎", deleted_at__isnull=True).first()
    if nunip:
        if not Category.objects.filter(section=nunip, name=NAME, deleted_at__isnull=True).exists():
            Category.objects.create(section=nunip, code="Z", name=NAME, direction=DIRECTION, question=QUESTION, order=80)
        _renumber(Category, nunip)
    for blog in Blog.objects.filter(name="눈잎", deleted_at__isnull=True):
        if not SiteCategory.objects.filter(blog=blog, parent=None, name=NAME, deleted_at__isnull=True).exists():
            last = SiteCategory.objects.filter(blog=blog, parent=None, deleted_at__isnull=True).order_by("-order").first()
            SiteCategory.objects.create(blog=blog, name=NAME, concept=CONCEPT, order=(last.order + 1) if last else 1)
        line = f"{blog.content} · {CONTENT}".strip(" ·")
        if NAME not in blog.content and len(line) <= 200:
            Blog.objects.filter(pk=blog.pk).update(content=line)


class Migration(migrations.Migration):
    dependencies = [
        ("blog_types", "0038_locator_map_concepts"),
        ("blog_rules", "0009_site_targets"),
    ]
    operations = [migrations.RunPython(forward, migrations.RunPython.noop)]
