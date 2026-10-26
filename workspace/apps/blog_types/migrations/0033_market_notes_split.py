"""밤밤 시황 노트를 코스피 · 나스닥 두 시리즈로 다시 나눈다 (2026-10-26 사용자: 코스피를 다음 날 아침에 보는 건 늦다).

1. '시황 노트' → '코스피 시황 노트' (그날 15:30 장 마감 뒤 한 편).
2. 0028 이 휴지통에 넣은 '나스닥' 소재를 되살려 '나스닥 시황 노트' (간밤 미국장을 아침에 한 편). 휴지통에 없으면 새로 만든다.
   0028 이 시황 노트로 옮긴 나스닥 글(제목에 나스닥만 있는 글)은 나스닥 시황 노트로 돌린다.
3. 밤밤 › 주식 카테고리 컨셉의 글 모양을 두 시리즈로. 밤밤 사이트 컨셉 문구도.
지우는 데이터 없음. 이름으로 찾아 있는 것만 손댄다.
"""
from django.db import migrations

KOSPI = ("코스피 시황 노트", "코스피 시황 노트: 한국 거래일마다 15:30 장 마감 뒤 그날 한 편 — 움직인 이유와 쌓이는 5거래일 표",
         "오늘 코스피 왜 이랬지")
NASDAQ = ("나스닥 시황 노트", "나스닥 시황 노트: 간밤 미국장 마감을 아침에 한 편 — 움직인 이유와 쌓이는 5거래일 표",
          "어젯밤 나스닥 왜 이랬지")
CONTENT = "코스피 시황 노트(그날 장 마감 뒤) · 나스닥 시황 노트(간밤 미국장, 아침) · 해외여행(경비·패스 계산형)"
STOCK_CONCEPT = "\n".join([
    "시황 노트 두 시리즈 (2026-10-26 사용자: 코스피를 다음 날 아침에 보는 건 늦다 → 다시 나눈다).",
    "- 코스피 시황 노트: 한국 거래일마다 그날 15:30 장 마감 뒤 한 편. 휴장일은 쉰다.",
    "- 나스닥 시황 노트: 미국 거래일마다 한국 시간 다음 날 아침에 한 편 (보통 화~토 아침). 미국 휴장 다음 아침은 쉰다.",
    "",
    "글 모양 (두 시리즈 공통):",
    "- 제목: 그날의 이야기 한 줄 + 끝에 시리즈 이름과 번호. 예) `반도체가 받친 코스피, 5,550 마감｜10.23 밤밤 코스피 시황 노트 No.1` · "
    "`메타 하나에 반도체 -6%, 나스닥 2.6% 급락｜10.22 밤밤 나스닥 시황 노트 No.1`. 날짜는 그 장의 날짜(나스닥은 미국 날짜), "
    "번호는 `콘텐츠/블로그_카페/데이터/코스피시황.csv` · `나스닥시황.csv` 의 번호. 숫자 나열·'정리'·'(2026)' 틀을 매번 쓰지 않는다.",
    "- 첫 줄: 맨 위 인용 상자 대신 말 거는 한두 줄로 연다. 날마다 다르게.",
    "- 바로 아래 지수 카드 그림 1장 (필수, 가공이미지). 오른 지수는 빨강, 내린 지수는 파랑. 이 그림이 글의 대표 사진이다.",
    "  코스피: 코스피·코스닥 종가 · 전일 대비 · 등락률 + 원·달러 환율, '10.26 장 마감 기준'.",
    "  나스닥: 나스닥·S&P500·다우 종가 · 전일 대비 · 등락률, '10.23 미국 마감 기준 (한국 10.24 새벽)'.",
    "- 그다음 서술 3~5줄: 그 장을 한 문장으로 + 그렇게 된 까닭.",
    "- 본문은 그날 맞는 덩어리를 골라 2~4개 (매일 같은 순서·같은 소제목 금지):",
    "  ① 오늘의 주인공 — 돈이 몰린(빠진) 테마 하나: 종목 · 등락률 · 거래대금 표(4~8종목) + '왜 이렇게 셌나' 2~4문장.",
    "  ② 장중 흐름 — 시가·저가·고가·종가를 시간 순서로 (하루 모양이 이야기인 날).",
    "  ③ 코스피: 누가 사고 팔았나 — 외국인·기관·개인 순매수 금액, 며칠째인지. 나스닥: 금리·달러·유가 중 그날 움직인 것.",
    "  ④ 코스피: 바깥 변수 — 간밤 미국장·환율·미국 지수선물. 나스닥: 실적·경제지표 발표 중 그날 움직인 것.",
    "  ⑤ 큰 종목 — 코스피는 삼성전자·SK하이닉스, 나스닥은 엔비디아·빅테크 중 그날 이야기가 있는 것만.",
    "- 5거래일 표 (매일, 이 시리즈만의 것): 그 시리즈 csv 의 최근 5줄 (작가가 그날 줄을 먼저 더한다). "
    "코스피는 날짜 · 코스피 · 등락률 · 코스닥 · 등락률 · 환율 · 외국인, 나스닥은 날짜 · 나스닥 · 등락률 · S&P500 · 등락률 · 다우. "
    "주의 마지막 거래일 글은 표 아래에 '이번 주' 한 줄 해설.",
    "- 소제목은 짧은 물음·말 (\"오늘은 왜 방산만 셌을까\", \"외국인은 또 팔았어요\"). 이모지 ✅ 를 소제목 앞에 써도 된다.",
    "- 끝: '내가 보는 다음 장' 2~3문장 — 지켜볼 선·일정 하나둘 (코스피 글은 오늘 밤 미국장에서 볼 것, 나스닥 글은 오늘 한국장에 이어질 것을 하나 넣어도 좋다). "
    "사거라·팔아라·목표가는 쓰지 않는다. 생각은 '제 생각엔'처럼 1인칭으로 담백하게. 마지막 한 줄 끝인사.",
    "- 사진: 지수 카드 1장은 꼭, 거기에 그날 이야기에 맞는 그림·사진 1~2장. 증권사 앱·HTS 화면 캡처는 쓰지 않는다.",
    "- 숫자는 거래소·언론 마감 기사로 확인하고 출처 한 줄.",
])
MARKER = "시황 노트 두 시리즈 (2026-10-26"


def _active(Category, section, name):
    return Category.objects.filter(section=section, name=name, deleted_at__isnull=True).order_by("order", "pk").first()


def _restore_nasdaq(apps, bam):
    """0028 이 휴지통에 넣은 '나스닥' 소재(와 그 아래)를 되살린다. 휴지통 묶음(core.TrashEntry)도 지운다.
    _base_manager: 휴지통 행까지 보는 manager (실제 모델의 objects 는 살아 있는 행만 본다)."""
    Category = apps.get_model("blog_types", "Category")
    TrashEntry = apps.get_model("core", "TrashEntry")
    cat = Category._base_manager.filter(section=bam, name="나스닥", deleted_at__isnull=False).order_by("-deleted_at", "-pk").first()
    if not cat:
        return None
    entry = TrashEntry.objects.filter(model_label="blog_types.category", object_key=str(cat.pk)).first()
    members = entry.members if entry else {"blog_types.category": [cat.pk]}
    for label, ids in members.items():
        app_label, model = label.split(".")
        apps.get_model(app_label, model)._base_manager.filter(pk__in=ids, deleted_at=cat.deleted_at).update(deleted_at=None)
    if entry:
        entry.delete()
    return Category.objects.get(pk=cat.pk)


def _renumber(Category, section):
    cats = sorted(Category.objects.filter(section=section, deleted_at__isnull=True), key=lambda c: (c.name == "그 외", c.order, c.pk))
    for i, c in enumerate(cats):
        Category.objects.filter(pk=c.pk).update(code=chr(65 + i), order=i + 1)


def forward(apps, schema_editor):
    Section = apps.get_model("blog_types", "Section")
    Category = apps.get_model("blog_types", "Category")
    SiteCategory = apps.get_model("blog_types", "SiteCategory")
    Blog = apps.get_model("blog_rules", "Blog")
    bam = Section.objects.filter(name="밤밤", deleted_at__isnull=True).first()
    if bam:
        kospi = _active(Category, bam, KOSPI[0]) or _active(Category, bam, "시황 노트") or _active(Category, bam, "코스피")
        if kospi:
            Category.objects.filter(pk=kospi.pk).update(name=KOSPI[0], direction=KOSPI[1], question=KOSPI[2], order=1)
        nasdaq = _active(Category, bam, NASDAQ[0]) or _active(Category, bam, "나스닥") or _restore_nasdaq(apps, bam)
        if nasdaq:
            Category.objects.filter(pk=nasdaq.pk).update(name=NASDAQ[0], direction=NASDAQ[1], question=NASDAQ[2], order=2)
        else:
            nasdaq = Category.objects.create(section=bam, code="B", name=NASDAQ[0], direction=NASDAQ[1], question=NASDAQ[2], order=2)
        if kospi:  # 0028 이 옮긴 나스닥 글을 돌려놓는다
            for label in ("writing", "naver_writing"):
                Post = apps.get_model(label, "Post")
                Post.objects.filter(bt_category=kospi, title__contains="나스닥").exclude(title__contains="코스피").update(bt_category=nasdaq)
        for other in Category.objects.filter(section=bam, deleted_at__isnull=True).exclude(pk__in=[c.pk for c in (kospi, nasdaq) if c]):
            if other.order <= 2:  # 해외 여행 등은 두 시황 노트 뒤로
                Category.objects.filter(pk=other.pk).update(order=other.order + 2)
        _renumber(Category, bam)
        Section.objects.filter(pk=bam.pk).update(note=CONTENT)
    Blog.objects.filter(name="밤밤", deleted_at__isnull=True).update(content=CONTENT)
    old = __import__("importlib").import_module("apps.blog_types.migrations.0028_sites_overhaul").STOCK_CONCEPT
    for cat in SiteCategory.objects.filter(blog__name="밤밤", name="주식", deleted_at__isnull=True):
        if MARKER in cat.concept:
            continue
        if old in cat.concept:
            cat.concept = cat.concept.replace(old, STOCK_CONCEPT)
        else:
            cat.concept = f"{cat.concept.rstrip()}\n\n{STOCK_CONCEPT}".strip()
        cat.save(update_fields=["concept"])


class Migration(migrations.Migration):
    dependencies = [
        ("blog_types", "0032_wordpress_looks_concepts"),
        ("core", "0007_posts_hub_menu"),
        ("blog_rules", "0009_site_targets"),
        ("writing", "0026_trash_nunip_kospi"),
        ("naver_writing", "0008_post_planned_on"),
    ]
    operations = [migrations.RunPython(forward, migrations.RunPython.noop)]
