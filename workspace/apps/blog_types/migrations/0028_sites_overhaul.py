"""사이트 정리 (2026-10-26 사용자): 제품소개 빼기 · 밤밤 시황 노트 · 눈잎 동물 · 첫 4주 하루 1편.

1. 밤밤 › 상품 추천 · 그 외(제품소개) 소재를 휴지통으로. 그 소재의 글(글 관리)과 그 글을 넣은 곳(매핑)도 함께 —
   블로그에서는 사용자가 이미 지웠다. 7일 안에는 휴지통에서 되돌릴 수 있다.
2. 밤밤 코스피 · 나스닥 → '시황 노트' 한 소재 (사용자가 아침에 돌린다: 전 거래일 코스피 마감 + 간밤 나스닥 마감을 한 편에).
   코스피 소재 이름을 바꾸고, 나스닥 글은 시황 노트로 옮긴 뒤 나스닥 소재를 휴지통으로. 밤밤 › 주식 카테고리 컨셉의 글 모양을 시황 노트로.
3. 눈잎에 '동물' 소재 + 사이트 카테고리 '동물' (티스토리 메뉴는 사용자가 만든다).
4. 사이트 컨셉 · 하루 편수 · 말투: 밤밤 하루 1편(첫 4주), 컨셉에서 상품 추천을 빼고, 눈잎 컨셉에 동물, 감상 규칙 한 줄.
이름으로 찾아 있는 것만 손댄다. 서버에서 이미 바꿔 둔 값은 건너뛴다.
"""
from django.db import migrations
from django.utils import timezone

PRODUCT = ("상품 추천", "그 외")
SECTIONS = {"writing.post": "티스토리 글쓰기", "naver_writing.post": "네이버 글쓰기"}

MARKET_DIRECTION = "시황 노트: 전 거래일 코스피 마감 + 간밤 나스닥 마감을 아침에 한 편 — 그날 움직인 이유와 쌓이는 5거래일 표"
MARKET_QUESTION = "어제 장 왜 이랬지, 간밤 미국은"
OLD_STOCK_HEAD = "코스피(한국장 마감)와 나스닥(미국장 마감)을 거래일마다 각각 한 편."
STOCK_CONCEPT = "\n".join([
    "시황 노트 (2026-10-26 사용자): 사용자가 아침에 돌린다 — 전 거래일 코스피 마감과 간밤 나스닥 마감을 한 편에.",
    "새 장이 있는 아침마다 한 편 (화~토 아침). 일요일·월요일 아침은 새 장이 없어 쉰다. 한국만 쉬었거나 미국만 쉰 날은 연 장만 쓴다.",
    "",
    "글 모양:",
    "- 제목: 그날의 이야기 한 줄 + 끝에 시리즈 이름과 번호. 예) `반도체가 받친 코스피, 간밤 나스닥은 메타에 -2.6%｜10.23 밤밤 시황 노트 No.3`. "
    "날짜는 코스피 장 날짜, 번호는 `콘텐츠/블로그_카페/데이터/시황노트.csv` 의 줄 수. 숫자 나열·'정리'·'(2026)' 틀을 매번 쓰지 않는다.",
    "- 첫 줄: 맨 위 인용 상자 대신 말 거는 한두 줄로 연다. 날마다 다르게.",
    "- 바로 아래 지수 카드 그림 1장 (필수, 가공이미지): 코스피·코스닥·나스닥·S&P500 종가 · 전일 대비 · 등락률 + 원·달러 환율, "
    "'10.23 코스피 마감 · 10.23 미국 마감 기준'. 오른 지수는 빨강, 내린 지수는 파랑. 이 그림이 글의 대표 사진이다.",
    "- 그다음 서술 3~5줄: 어제 한국장 한 문장 + 간밤 미국장 한 문장 + 둘이 어떻게 이어지나.",
    "- 본문은 그날 맞는 덩어리를 골라 2~4개 (매일 같은 순서·같은 소제목 금지):",
    "  ① 오늘의 주인공 — 돈이 몰린(빠진) 테마 하나: 종목 · 등락률 · 거래대금 표(4~8종목) + '왜 이렇게 셌나' 2~4문장.",
    "  ② 장중 흐름 — 시가·저가·고가·종가를 시간 순서로 (하루 모양이 이야기인 날).",
    "  ③ 누가 사고 팔았나 — 외국인·기관·개인 순매수 금액, 며칠째인지.",
    "  ④ 간밤 미국장 — 빅테크·반도체·금리·유가 중 그날 움직인 것만.",
    "  ⑤ 큰 종목 — 삼성전자·SK하이닉스·엔비디아 중 그날 이야기가 있는 것만.",
    "- 5거래일 표 (매일, 이 시리즈만의 것): 날짜 · 코스피 · 등락률 · 나스닥 · 등락률 · 환율 최근 5줄. 시황노트.csv 에서 옮긴다 (작가가 그날 줄을 먼저 더한다). "
    "주의 마지막 거래일 글은 표 아래에 '이번 주' 한 줄 해설.",
    "- 소제목은 짧은 물음·말 (\"오늘은 왜 방산만 셌을까\", \"외국인은 또 팔았어요\"). 이모지 ✅ 를 소제목 앞에 써도 된다.",
    "- 끝: '내가 보는 다음 장' 2~3문장 — 지켜볼 선·일정 하나둘. 사거라·팔아라·목표가는 쓰지 않는다. 생각은 '제 생각엔'처럼 1인칭으로 담백하게. 마지막 한 줄 끝인사.",
    "- 사진: 지수 카드 1장은 꼭, 거기에 그날 이야기에 맞는 그림·사진 1~2장. 증권사 앱·HTS 화면 캡처는 쓰지 않는다.",
    "- 숫자는 거래소·언론 마감 기사로 확인하고 출처 한 줄.",
])

ANIMAL_DIRECTION = "동물 한 종을 잡고 신기한 사실 · 새 연구 · 알던 것의 반전(잘못 퍼진 상식 바로잡기)을 근거와 함께, 가볍게 감상을 섞어"
ANIMAL_QUESTION = "이 동물 이런 게 진짜야?"
ANIMAL_CONCEPT = "\n".join([
    "동물 한 종(또는 한 무리)을 잡고 흥미로운 사실 하나를 중심으로 — 신기한 능력 · 새 연구 결과 · 다들 아는 것의 반전(잘못 퍼진 상식 바로잡기).",
    "",
    "글 모양 (2026-10-26 사용자):",
    "- 제목: 궁금증 그대로. 예) `금붕어 기억력 3초는 틀렸다, 실험으로는 몇 달`. '총정리'·'TOP N'·'놀라운' 금지.",
    "- 맨 위 인용 상자 대신 첫 두세 줄에 핵심 사실 + 가벼운 감상 한 줄.",
    "- 본문 3~5 덩어리: 무엇이 신기한가 → 어떻게 알았나(연구·관찰, 연도·기관) → 왜 그런가(원리) → 잘못 알던 것 또는 더 재미있는 사실 → 마무리 감상.",
    "- 감상: 사실에 대한 반응·생각만 2~4곳 (\"이건 좀 놀라웠어요\", \"개인적으로는 이쪽이 더 끌려요\"). 키워 봤다·직접 봤다 같은 겪은 척은 쓰지 않는다. "
    "이모지 2~4개, 짧은 줄바꿈.",
    "- 근거: 논문·대학·박물관·국립생물자원관·동물원 공식·내셔널지오그래픽 같은 1차·전문 출처로 확인하고 글 끝 '참고'에. 인터넷 '상식' 글은 근거로 쓰지 않는다.",
    "- 사진: 그 동물이 실제로 찍힌 무료 사진 1~3장 (위키미디어 공용·Unsplash·Pexels). 그림이 빨리 읽히는 곳만 가공이미지 1장.",
    "- 길이: 짧고 가볍게 (소제목 3~5개).",
])

BLOG_CONTENT = {
    "밤밤": "시황 노트(전 거래일 코스피 + 간밤 나스닥, 아침 한 편) · 해외여행(경비·패스 계산형)",
}
DAILY_NOTE = "첫 4주(11/23까지) 하루 1편 (2026-10-26)"
TONE = {  # 사이트 → (원래 값 그대로일 때 바꿀 값, 없으면 뒤에 덧붙일 한 줄)
    "밤밤": ("정보성 해요체, 눈잎보다 간결하게.",
            "정보성 해요체, 담백하게 — 감상 없이 숫자와 까닭으로. 1인칭은 끝의 '내가 보는 다음 장'에서만."),
    "눈잎": ("", "동물 카테고리만 감상·이모지를 가볍게 (writing_site_눈잎.md '감상'). 공고·정책·공모주는 담백하게."),
    "black_lukey": ("", "갈 곳·작품마다 감상 한두 줄과 짧은 줄바꿈은 좋다 (writing_site_black_lukey.md '감상'). 겪은 척은 하지 않는다."),
}


def _active(Category, section, name):
    return Category.objects.filter(section=section, name=name, deleted_at__isnull=True).order_by("order", "pk").first()


def _trash(apps, label, key, title, section, members, now):
    """휴지통 한 묶음: 공통 휴지통(core.TrashEntry)에 이름·위치·PK 목록을 남기고 행마다 deleted_at."""
    TrashEntry = apps.get_model("core", "TrashEntry")
    TrashEntry.objects.filter(model_label=label, object_key=str(key)).delete()
    TrashEntry.objects.create(model_label=label, object_key=str(key), title=title[:200], section=section,
                              deleted_at=now, members=members)
    for member, ids in members.items():
        app_label, model = member.split(".")
        apps.get_model(app_label, model).objects.filter(pk__in=ids, deleted_at__isnull=True).update(deleted_at=now)


def _trash_category(apps, cat, now):
    PostType = apps.get_model("blog_types", "PostType")
    SubType = apps.get_model("blog_types", "SubType")
    types = list(PostType.objects.filter(category=cat, deleted_at__isnull=True).values_list("pk", flat=True))
    subs = list(SubType.objects.filter(post_type__in=types, deleted_at__isnull=True).values_list("pk", flat=True))
    members = {"blog_types.category": [cat.pk]}
    if types:
        members["blog_types.posttype"] = types
    if subs:
        members["blog_types.subtype"] = subs
    _trash(apps, "blog_types.category", cat.pk, f"{cat.section.name} › {cat.name}", "카테고리 관리 · 카테고리", members, now)


def _trash_posts(apps, cat, now):
    Placement = apps.get_model("blog_types", "Placement")
    for label, fk in (("writing.post", "tistory_post"), ("naver_writing.post", "naver_post")):
        Post = apps.get_model(*label.split("."))
        for post in Post.objects.filter(bt_category=cat, deleted_at__isnull=True):
            members = {label: [post.pk]}
            pls = list(Placement.objects.filter(**{fk: post.pk}, deleted_at__isnull=True).values_list("pk", flat=True))
            if pls:
                members["blog_types.placement"] = pls
            _trash(apps, label, post.pk, post.title, SECTIONS[label], members, now)


def _renumber(Category, section):
    """기호 A, B, C … 와 순서를 다시 매긴다. '그 외'는 맨 뒤."""
    cats = sorted(Category.objects.filter(section=section, deleted_at__isnull=True), key=lambda c: (c.name == "그 외", c.order, c.pk))
    for i, c in enumerate(cats):
        Category.objects.filter(pk=c.pk).update(code=chr(65 + i), order=i + 1)


def forward(apps, schema_editor):
    Section = apps.get_model("blog_types", "Section")
    Category = apps.get_model("blog_types", "Category")
    SiteCategory = apps.get_model("blog_types", "SiteCategory")
    Blog = apps.get_model("blog_rules", "Blog")
    SiteTemplate = apps.get_model("site_templates", "SiteTemplate")
    FixedTopic = apps.get_model("routines", "FixedTopic")
    now = timezone.now()
    bam = Section.objects.filter(name="밤밤", deleted_at__isnull=True).first()
    nunip = Section.objects.filter(name="눈잎", deleted_at__isnull=True).first()

    if bam:
        for name in PRODUCT:  # 1. 제품소개
            cat = _active(Category, bam, name)
            if cat:
                _trash_posts(apps, cat, now)
                FixedTopic.objects.filter(category=cat).update(category=None)
                _trash_category(apps, cat, now)
        kospi, nasdaq = _active(Category, bam, "코스피"), _active(Category, bam, "나스닥")  # 2. 시황 노트
        market = kospi or nasdaq
        if market:
            Category.objects.filter(pk=market.pk).update(name="시황 노트", direction=MARKET_DIRECTION, question=MARKET_QUESTION)
            other = nasdaq if market == kospi else None
            if other:
                for label in ("writing", "naver_writing"):
                    apps.get_model(label, "Post").objects.filter(bt_category=other).update(bt_category=market, bt_type=None, bt_sub=None)
                FixedTopic.objects.filter(category=other).update(category=market)
                _trash_category(apps, other, now)
        _renumber(Category, bam)
        Section.objects.filter(pk=bam.pk).update(note=BLOG_CONTENT["밤밤"])
    for cat in SiteCategory.objects.filter(blog__name="밤밤", name="주식", deleted_at__isnull=True):
        if "시황 노트 (2026-10-26" in cat.concept:
            continue
        head = cat.concept.split(OLD_STOCK_HEAD)[0].rstrip() if OLD_STOCK_HEAD in cat.concept else cat.concept.rstrip()
        cat.concept = f"{head}\n\n{STOCK_CONCEPT}" if head else STOCK_CONCEPT
        cat.save(update_fields=["concept"])

    if nunip:  # 3. 동물
        if not _active(Category, nunip, "동물"):
            Category.objects.create(section=nunip, code="Z", name="동물", direction=ANIMAL_DIRECTION, question=ANIMAL_QUESTION,
                                    order=80)
        _renumber(Category, nunip)
    for blog in Blog.objects.filter(name="눈잎", deleted_at__isnull=True):
        if not SiteCategory.objects.filter(blog=blog, parent=None, name="동물", deleted_at__isnull=True).exists():
            last = SiteCategory.objects.filter(blog=blog, parent=None).order_by("-order").first()
            SiteCategory.objects.create(blog=blog, name="동물", concept=ANIMAL_CONCEPT, order=(last.order + 1) if last else 1)
        if "동물" not in blog.content:
            Blog.objects.filter(pk=blog.pk).update(content=f"{blog.content} · 동물(신기한 이야기)".strip(" ·")[:200])

    for blog in Blog.objects.filter(name="밤밤", deleted_at__isnull=True):  # 4. 컨셉 · 하루 편수
        Blog.objects.filter(pk=blog.pk).update(content=BLOG_CONTENT["밤밤"], daily=1, daily_note=DAILY_NOTE)
    for name, (old, new) in TONE.items():
        for tpl in SiteTemplate.objects.filter(blog__name=name):
            if old and tpl.tone.strip() == old:
                tpl.tone = new
            elif new not in tpl.tone:
                tpl.tone = f"{tpl.tone.rstrip()}\n{new}".strip()
            else:
                continue
            tpl.save(update_fields=["tone"])


class Migration(migrations.Migration):
    dependencies = [
        ("blog_types", "0027_bambam_other_product"),
        ("blog_rules", "0009_site_targets"),
        ("site_templates", "0010_naver_parking_address"),
        ("routines", "0021_topic_daily"),
        ("writing", "0024_anime_dragonball_conan"),
        ("naver_writing", "0008_post_planned_on"),
        ("core", "0007_posts_hub_menu"),
    ]
    operations = [migrations.RunPython(forward, migrations.RunPython.noop)]
