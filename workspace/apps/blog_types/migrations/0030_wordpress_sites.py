"""워드프레스 jinbaam.com 을 글쓰기 루틴에 (2026-10-26 사용자) + 동물은 하지 않는다.

1. 워드프레스: 운영 · 주소 · 컨셉 · 체크, 글 분류(사이트 > 소재)와 사이트 카테고리 넷 — 산과 캠핑 · 드라이브·자동차 ·
   국내여행(외국인 관광객용 영어 본문 + 끝에 일본어·중국어 짧은 요약) · 해외여행(영어 N박 N일). 말투·구성·꼭 지킬 것.
   붙여넣기 포맷: 사진은 주소 그대로 넣는다 (블록 에디터가 이미지 블록으로 바꾼다).
2. 눈잎 › 동물 소재·사이트 카테고리를 휴지통으로 (그 글·넣은 곳도), 눈잎 컨셉·말투에서 동물 줄을 뺀다.
3. 자동차 출시 소식은 워드프레스 › 드라이브·자동차로: black_lukey › 출시 컨셉에서 자동차를 뺀다.
이름으로 찾아 있는 것만 손댄다. 서버에서 이미 바꿔 둔 값은 건너뛴다.
"""
from importlib import import_module

from django.db import migrations
from django.utils import timezone

SITE = "워드프레스"
ADDRESS = "https://jinbaam.com/"
CONTENT = "산과 캠핑 · 드라이브·자동차 · 국내여행(외국인용 영어 + 일본어·중국어 요약) · 해외여행(영어 N박 N일)"
CHECKS = [
    "국내여행·해외여행은 영어 본문. 국내여행은 끝에 일본어·중국어 짧은 요약",
    "영어 원고는 제작 정보에 한국어 대역 — 사용자가 읽고 확인한다",
    "다른 블로그 글을 번역하지 않는다 (black_lukey 지역 · 밤밤 해외여행과 같은 곳은 새 시선으로)",
]
OLD_CHECK = "요금제·설치형·용도는 마지막에 사용자와 정함"

MATERIALS = [  # (소재, 방향 = 글쓰기 컨셉, 독자의 질문)
    ("산과 캠핑", "산 하나를 잡고 그 계절에 가장 좋은 모습(벚꽃·철쭉·신록·계곡·단풍·억새·상고대·눈꽃·일출)으로 — 등산 코스 · 산 아래 캠핑장 · "
                "케이블카·둘레길 나들이 중 그 산에 자연스러운 조합", "이번 계절 어느 산 가지, 어떻게 오르고 어디서 묵지"),
    ("드라이브·자동차", "차 가진 사람들이 궁금해하는 것 전부 — 신차·연식 변경 · 기름값·통행료·자동차세·보험·검사 같은 돈과 제도 · "
                     "자동차 기능·상식 · 드라이브 코스", "이 차 뭐가 달라졌지, 내 차에 얼마 들지, 이번 주말 어디로 달리지"),
    ("국내여행", "외국인 관광객에게 한국의 한 지역을 영어로 소개 (black_lukey 지역 놀거리처럼 코스·장소·정보 카드), 끝에 일본어·중국어 짧은 요약",
              "Where should I go in Korea, and how do I get there"),
    ("해외여행", "해외 한 도시·나라의 N박 N일 일정을 영어로 — 일정표 · 교통 · 경비 · 장소 카드 (밤밤 해외여행과 같은 짜임)",
              "How do I plan N days in this city"),
]

MOUNTAIN = "\n".join([
    "산 하나를 잡고 그 계절의 가장 좋은 모습으로 소개한다 (2026-10-26 사용자).",
    "",
    "무엇을 쓸지:",
    "- 계절: 봄 벚꽃·진달래·철쭉 / 여름 신록·계곡·숲 그늘 / 가을 단풍·억새 / 겨울 상고대·눈꽃·해돋이. 2~4주 뒤 절정인 산을 먼저.",
    "- 초점은 그 산에 자연스러운 것으로 고른다 — 억지로 셋을 다 넣지 않는다:",
    "  ① 등산: 코스(들머리·날머리·거리·시간·난이도) 중심. 정상 풍경이 이야기인 산.",
    "  ② 산 + 캠핑: 등산 뒤 하룻밤, 또는 캠핑이 주인공인 산 (계곡 옆 야영장·국립공원 야영장).",
    "  ③ 산 나들이: 케이블카·둘레길·사찰·전망대 — 오르지 않고도 즐기는 산.",
    "- 같은 산은 60일 안에 다시 쓰지 않는다. 지역을 돌린다.",
    "",
    "글 모양:",
    "- 맨 위 인용(이 산 · 이 계절 · 누구에게, 2~3문장) → 한눈에 보는 표(가기 좋은 때 · 코스 · 걸리는 시간 · 난이도 · 예약할 것) → 본문 → 마무리 서술.",
    "- 등산 코스는 `::: 장소 | 코스 이름` 카드: 🥾 코스(들머리 → 정상 → 날머리) · ⏱️ 시간·거리 · 📈 난이도 · 🚌 가는 법 · 🅿️ 주차 · 📍 들머리 지도 링크.",
    "- 캠핑장은 `::: 장소 | 야영장 이름` 카드: ⛺ 사이트 수·종류 · 🔌 전기·온수 · 💳 요금 · 🎫 예약(열리는 날·주소) · 🐕 반려견 · 📍 지도. 고캠핑 데이터로 확인.",
    "- 그 계절의 절정 시기는 산림청·국립공원공단 예측을 쓰고, 예측이 갈리면 둘 다 적는다.",
    "- 사진: 그 산이 그 계절에 실제로 찍힌 무료 사진 2~4장. 경험(\"올라 보니\")은 쓰지 않는다. 감상은 풍경에 대한 한 줄까지.",
])
CAR = "\n".join([
    "차 가진 사람들이 흥미로워하는 것 전부 (2026-10-26 사용자). 신차 출시 소식도 여기 (black_lukey › 출시는 차를 다루지 않는다).",
    "",
    "글 종류를 돌린다:",
    "- 신차·연식 변경: 달라진 점 · 가격 · 트림 비교표 · 지금 살까 기다릴까.",
    "- 돈과 제도: 기름값(오피넷 주간 추이) · 통행료 · 자동차세(연납 할인) · 정기검사 · 과태료 · 보험 갱신 — 계산 예시 표 하나를 꼭.",
    "- 기능·상식: 계기판 경고등 · 겨울철 배터리·타이어 · 전기차 충전 — 원리와 할 일 순서.",
    "- 드라이브 코스: 출발지 · 거리 · 걸리는 시간 · 들를 곳 카드 · 통행료·기름값 합계.",
    "",
    "글 모양: 맨 위 인용(결론 2~3문장, 기준일) → 표 하나 → 질문형 소제목 2~4개 → 판단 한 줄로 마무리.",
    "- 숫자(가격·세금·요금)는 제조사·정부(위택스·한국도로공사·오피넷·교통안전공단) 공지로 확인하고 기준일을 적는다.",
    "- 써 본 척(\"타 보니\") 금지. 시승 후기는 '타 본 사람들은 …'으로 출처를 단다.",
])
KOREA = "\n".join([
    "외국인 관광객에게 한국의 한 지역을 영어로 소개한다 (2026-10-26 사용자: black_lukey 지역 놀거리처럼). 독자: 영미권·일본·중국 관광객.",
    "",
    "글 모양:",
    "- 본문은 영어. 제목도 영어 (예: `Gyeongju in Autumn: A One-Day Route from Seoul by KTX`).",
    "- 맨 위 인용(who · when · the route in one line) → Day plan 표(time · place · how to move · cost) → 장소마다 `## 1. Place: one-line point` → 사진 1장 이상 → 2~4문장 → 정보 카드.",
    "- 정보 카드 `::: 장소 | Place name (한글 이름)` : ⏰ Hours · 💳 Admission (KRW) · 🚇 Getting there (subway line·station·exit in English, KTX/bus from Seoul or Incheon Airport) · "
    "🗣️ English support · 💡 Foreigner tip (T-money, tax refund, booking without a Korean phone number) · 📍 Google Maps 링크.",
    "- 외국인이 막히는 것을 꼭 넣는다: 한국 전화번호 없이 예약 · 외국 카드 결제 · 영어 안내 여부 · 공항에서 가는 법.",
    "- 끝에 `## 日本語まとめ` 3~5줄, `## 中文简介` (간체) 3~5줄 — 본문을 요약만, 새 정보 없이. 숫자·장소 이름은 본문과 같게.",
    "- 사진은 그 장소가 실제로 찍힌 무료 사진 (공공누리·위키미디어·Unsplash·Pexels), 620 가운데. 감상은 장소마다 한 줄까지.",
    "- black_lukey 의 같은 지역 글을 번역하지 않는다 — 외국인 시선(교통·언어·결제)으로 새로 짠다.",
])
ABROAD = "\n".join([
    "해외 한 도시·나라의 N박 N일을 영어로 (2026-10-26 사용자: 밤밤 해외여행과 같은 느낌).",
    "",
    "글 모양:",
    "- 본문·제목 영어 (예: `3 Days in Taipei: Day-by-Day Route, Transport and Budget`).",
    "- 맨 위 인용(who · how many days · base area) → Itinerary 표(day · area · route · transport · daily cost) → Airport to city 비교표 → Day 1, Day 2 … (장소마다 사진·2~4문장·`::: 장소` 카드: Hours · Admission · Getting there · 📍 Google Maps) → Budget 표 → Before you go 체크리스트.",
    "- 비자·입국 규정·환율은 공식 출처와 기준일. 미국·영국·호주 등 영어권 여권 기준으로 쓰고, 다르면 그렇게 적는다.",
    "- 밤밤의 한국어 글을 번역하지 않는다. 같은 도시는 밤밤과 21일 안에 겹치지 않게.",
])
CONCEPTS = {"산과 캠핑": MOUNTAIN, "드라이브·자동차": CAR, "국내여행": KOREA, "해외여행": ABROAD}

TEMPLATE = dict(
    tone="한국어 카테고리(산과 캠핑·드라이브·자동차)는 정보성 해요체, 짧은 문단, 풍경에 대한 감상 한 줄까지. "
         "영어 카테고리(국내여행·해외여행)는 쉬운 영어 — 짧은 문장, 현지 고유명사는 영어 + 한글(또는 현지어) 병기.",
    structure="카테고리 컨셉의 '글 모양'을 따른다. 공통: 맨 위 인용(2~3문장) → 표 하나 → 본문(정보 카드) → 마무리 서술.",
    rules="사진은 실제 그 장소·그 계절이 찍힌 무료 사진만, 620 가운데. 지도는 구글 지도 링크(외국인용). "
          "영어 원고는 제작 정보에 '한국어 대역'을 붙인다 (본문 밖). 다른 블로그 글을 번역하지 않는다.",
)
WP_FORMAT_OLD = "사진은 넣지 않는다 (미디어 라이브러리에 직접 올린다). 접은 글(details)은 쓰지 않는다."
WP_FORMAT_NEW = ("사진은 `![설명](주소)` 그대로 둔다 — 블록 에디터에 붙이면 이미지 블록이 된다 (설명이 대체 텍스트). "
                 "사진 출처 줄은 이미지 바로 아래 기울임 한 줄. 접은 글(details)은 쓰지 않는다.")
ANIMAL_LINE = "동물 카테고리만 감상·이모지를 가볍게 (writing_site_눈잎.md '감상'). 공고·정책·공모주는 담백하게."
NUNIP_ANIMAL = " · 동물(신기한 이야기)"


def forward(apps, schema_editor):
    o28 = import_module("apps.blog_types.migrations.0028_sites_overhaul")
    Section = apps.get_model("blog_types", "Section")
    Category = apps.get_model("blog_types", "Category")
    SiteCategory = apps.get_model("blog_types", "SiteCategory")
    Placement = apps.get_model("blog_types", "Placement")
    Blog = apps.get_model("blog_rules", "Blog")
    Rule = apps.get_model("blog_rules", "Rule")
    SiteTemplate = apps.get_model("site_templates", "SiteTemplate")
    PlatformFormat = apps.get_model("site_templates", "PlatformFormat")
    now = timezone.now()

    # 1. 워드프레스
    wp = Blog.objects.filter(platform="wordpress", deleted_at__isnull=True).first()
    if wp:
        Blog.objects.filter(pk=wp.pk).update(status="active", address=wp.address or ADDRESS, routine=True, content=CONTENT,
                                             daily=wp.daily or len(MATERIALS))
        Rule.objects.filter(blog=wp, body=OLD_CHECK, deleted_at__isnull=True).update(deleted_at=now)
        for i, body in enumerate(CHECKS, start=1):
            if not Rule.objects.filter(blog=wp, body=body, deleted_at__isnull=True).exists():
                Rule.objects.create(blog=wp, group="check", body=body, note="2026-10-26 사용자", order=i)
        top = SiteCategory.objects.filter(blog=wp, parent=None, deleted_at__isnull=True)
        for i, (name, concept) in enumerate(CONCEPTS.items(), start=1):
            cat = top.filter(name=name).first()
            if cat is None:
                SiteCategory.objects.create(blog=wp, name=name, concept=concept, order=i)
            elif not cat.concept.strip():
                SiteCategory.objects.filter(pk=cat.pk).update(concept=concept)
        tpl, _ = SiteTemplate.objects.get_or_create(blog=wp)
        changed = [f for f, v in TEMPLATE.items() if not getattr(tpl, f).strip()]
        for f in changed:
            setattr(tpl, f, TEMPLATE[f])
        if changed:
            tpl.save(update_fields=changed)
        section = Section.objects.filter(name=wp.name, deleted_at__isnull=True).first()
        if section is None:
            last = Section.objects.filter(deleted_at__isnull=True).exclude(name="memorily").order_by("-order").first()
            section = Section.objects.create(name=wp.name, note=CONTENT, order=(last.order + 1) if last else 9)
        for i, (name, direction, question) in enumerate(MATERIALS):
            if not o28._active(Category, section, name):
                Category.objects.create(section=section, code=chr(65 + i), name=name, direction=direction, question=question, order=i + 1)
    for fmt in PlatformFormat.objects.filter(platform="wordpress"):
        if WP_FORMAT_OLD in fmt.guide:
            fmt.guide = fmt.guide.replace(WP_FORMAT_OLD, WP_FORMAT_NEW)
            fmt.save(update_fields=["guide"])

    # 2. 동물은 하지 않는다
    nunip = Section.objects.filter(name="눈잎", deleted_at__isnull=True).first()
    animal = o28._active(Category, nunip, "동물") if nunip else None
    if animal:
        o28._trash_posts(apps, animal, now)
        o28._trash_category(apps, animal, now)
        o28._renumber(Category, nunip)
    for cat in SiteCategory.objects.filter(blog__name="눈잎", name="동물", parent=None, deleted_at__isnull=True):
        members = {"blog_types.sitecategory": [cat.pk]}
        pls = list(Placement.objects.filter(site_category=cat, deleted_at__isnull=True).values_list("pk", flat=True))
        if pls:
            members["blog_types.placement"] = pls
        o28._trash(apps, "blog_types.sitecategory", cat.pk, f"눈잎 › {cat.name}", "카테고리 관리 · 사이트 카테고리", members, now)
    for blog in Blog.objects.filter(name="눈잎", deleted_at__isnull=True):
        if NUNIP_ANIMAL in blog.content:
            Blog.objects.filter(pk=blog.pk).update(content=blog.content.replace(NUNIP_ANIMAL, ""))
    for tpl in SiteTemplate.objects.filter(blog__name="눈잎"):
        if ANIMAL_LINE in tpl.tone:
            tpl.tone = "\n".join(line for line in tpl.tone.splitlines() if line.strip() != ANIMAL_LINE).strip()
            tpl.save(update_fields=["tone"])

    # 3. 자동차 출시는 워드프레스
    for cat in SiteCategory.objects.filter(blog__name="black_lukey", name="출시", deleted_at__isnull=True):
        if "·자동차 등" in cat.concept:
            cat.concept = cat.concept.replace("·자동차 등", " 등")
            cat.save(update_fields=["concept"])


class Migration(migrations.Migration):
    dependencies = [
        ("blog_types", "0029_placement_changed"),
        ("blog_rules", "0009_site_targets"),
        ("site_templates", "0010_naver_parking_address"),
        ("writing", "0025_post_source"),
        ("core", "0007_posts_hub_menu"),
    ]
    operations = [migrations.RunPython(forward, migrations.RunPython.noop)]
