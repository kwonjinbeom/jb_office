"""memorily 총정리 카테고리 3개 (2026-10-31 사용자: memorily 글감·조회수가 부진 → 묶음으로 보여 주는 총정리 카테고리를 늘린다).

구글 트렌드(한국, 지난 12개월)로 고른 것: 무료 AI 툴(무료 ai ≈ 스팀 할인의 4.6배) · 이달의 AI(ai 뉴스) · IT 할인(블랙프라이데이 · 광군제, 11월에 크게 뛴다).
1. 글 분류 memorily 에 소재 3개 (B · C · D). memorily 는 글쓰기 루틴을 끈 사이트라 일일 분량에는 들지 않고, 커스텀 글쓰기에서 소재로 고른다.
2. 사이트 카테고리 memorily › 무료 AI 툴 · 이달의 AI · IT 할인: 글 모양은 black_lukey › 출시의 짜임(결론 → 일정 표 → 알려진 것 → 살까 기다릴까 → 공식 소식)을
   소재에 맞게 + 실제 사진 + 정리 그림 (예시 dhsy.tistory.com/420 의 그림처럼 한눈에, 다만 회사 PT 자료처럼 정적이고 깔끔하게 —
   콘텐츠/블로그_카페/변환그림/정리카드.py). 이달의 AI 는 AI 와 같은 소제목 빨간 막대.
3. memorily › 애니: 분기 신작 글은 환산기 짜임이 아니라 사용자가 쓰는 애니 글처럼 평범하게 (정리 그림 없음).
같은 글이 작가 파일(일일루틴/프롬프트/writing_site_memorily.md)에도 있다 — 고칠 때 둘 다. 컨셉이 이미 있으면 건드리지 않는다. 지우는 데이터 없음.
"""
from django.db import migrations

FIGURES = """정리 그림 (가공이미지, 2026-10-31 사용자 — 한눈에 정보가 들어오되 회사 PT 자료처럼 정적이고 깔끔하게):
- `python 콘텐츠/블로그_카페/변환그림/정리카드.py <설계 json> 콘텐츠/블로그_카페/변환그림/<글 번호>/<이름>.png` 로 그린다.
  견본 설계는 `변환그림/정리카드_견본/{prefix}_*.json` — 모양만 따르고 이름·숫자·날짜는 이 글의 사실로 바꾼다 (theme {theme}).
- 맨 위 인용 바로 다음에 표지 그림 1장(필수) + 본문에 1~2장. 한 글에 같은 layout 을 두 번 쓰지 않는다.
- 그림은 한눈에(요약 · 날짜 · 고르기), 표·카드는 자세히 — 표를 그대로 옮긴 그림은 만들지 않는다.
- 그림 속 숫자·날짜는 사실 점검을 마친 것만. foot 에 기준일 · 출처 (`11월 1일 각 서비스 요금 페이지 기준`).
- 실제 사진은 그림과 따로 넣는다 (실용적인 것: 공식 화면 · 보도 이미지 · 제품 실물). 생성형 AI 로 만든 가짜 사진은 쓰지 않는다."""

TOOL = """무료 AI 툴: 용도(이미지 · 영상 · PPT · 글쓰기 · 코딩 · 음성 …)마다 돈 안 내고 어디까지 되는지 총정리. 결론 먼저, 확인된 것 위주로 담백하게.
글 모양 (black_lukey › 출시의 짜임을 이 소재에 맞게):
- 순서: 맨 위 인용(결론 2~3문장: 이 용도면 무엇 · 무료 범위 한 줄) → 표지 그림(grid '용도별 무료 AI 한눈에') → 한눈에 표(툴 · 무료로 되는 것 · 무료 한도 · 한국어 · 상업 이용 · 가입) → 툴마다 소제목 → 비교 그림(compare) → 고르기 그림(pick '나한테 맞는 무료 AI') → 무료로 쓸 때 주의(상업 이용 · 저작권 · 개인정보 · 워터마크) → 공식 요금 페이지 보는 곳 → 참고 줄.
- 툴마다 `## 툴 이름 — 한 줄 포인트`: 실제 화면 사진 1장(공식 화면 · 보도 이미지, 또는 직접 연 화면 캡처 — 로그인 정보 · 개인 정보가 보이지 않게) → 서술 2~3문장(무엇을 잘하나 · 무료에서 막히는 곳) → `::: 제품 | 툴 이름` 카드: 💳 무료 범위 · 💰 유료 요금(월, 원화) · 🇰🇷 한국어 · 🧾 상업 이용 · 🔑 가입 · 🔗 바로가기(공식 주소).
- 무료 범위는 자주 바뀐다: 표 아래에 '○월 ○일 각 서비스 요금 페이지 기준' 한 줄. 확인 못 한 한도는 쓰지 않는다.
- 써 본 척하지 않는다. 다른 사람 후기는 '써 본 사람들은 …' + 출처.

""" + FIGURES.format(prefix="무료AI툴", theme="ai_tool · 청록")

MONTH = """이달의 AI: 한 달 동안 바뀐 AI를 한 편에 (매월 1~3일, 지난달). 재료는 그달 memorily › AI 소식 원고와 공식 발표.
날마다 쓴 AI 소식을 그대로 옮기지 않고, 한 달을 묶어 '무엇이 가장 컸나 · 나는 뭘 바꾸면 되나'로.
글 모양 (black_lukey › 출시의 짜임을 이 소재에 맞게):
- 순서: 맨 위 인용(이달 가장 큰 변화 2~3문장) → 표지 그림(timeline '○월 AI, 날짜로 한눈에', 가장 큰 것 hot) → 날짜순 표(날짜 · 도구 · 바뀐 것 · 누구에게) → 핵심 숫자 그림(number, 숫자로 말할 변화가 있을 때) → 도구마다 소제목 → 확인된 것 · 소문 · 믿지 않아도 되는 것 → 다음 달 볼 것(발표 예정 · 요금 적용일) → 공식 소식 보는 곳 → 참고 줄.
- 도구마다 `## 도구 — 무엇이 바뀌었나`: 실제 사진 1장(공식 발표 이미지 · 제품 화면) → 2~4줄 → `::: 제품 | 도구 이름` 카드: 📅 발표 · 적용일 · 💳 대상 · 요금제 · 🇰🇷 한국 사용 · 🔗 공식 발표.
- 그달 AI 소식 글의 발행 주소가 있으면 그 항목 끝에 '자세히: ○월 ○일 AI 소식' 링크.
- 소제목: 앞의 빨간 세로 막대는 붙여넣는 HTML 이 단다 (AI 와 같다).

""" + FIGURES.format(prefix="이달의AI", theme="ai_month · 빨강 #e03131")

SALE = """IT 할인: 광군제 · 블랙프라이데이 · 사이버먼데이 · 스팀 세일처럼 날짜가 정해진 IT 할인 행사를 한 편에 (행사 7~10일 전).
기기 · 주변기기 · 소프트웨어 · 게임만 — 옷 · 화장품은 다루지 않는다. 기기 한 대 · 게임 한 편의 출시는 black_lukey › 출시가 쓴다.
글 모양 (black_lukey › 출시의 짜임: 결론 → 일정 표 → 알려진 것 → 살까 기다릴까 → 공식 소식):
- 순서: 맨 위 인용(결론 2~3문장: 언제 무엇을 사면 좋은지) → 표지 그림(timeline 'IT 할인 날짜') → 행사 일정 표(행사 · 기간(한국시간) · 어디서 · 잘 맞는 물건) → 행사마다 소제목 → 행사 비교 그림(panels) → 지금 살까 기다릴까(pick 그림 + 서술) → 직구 체크(면세 한도 · 배송 기간 · 전압 · AS — 숫자는 관세청 공식 안내로) → 공식 소식 보는 곳 → 참고 줄.
- 행사마다 `## 행사 이름 · 기간`: 실제 사진 1~2장(행사 공식 페이지 화면 · 제품 실물) → 서술 2~3문장 → `::: 제품 | 행사 이름` 카드: 📅 기간(한국시간) · 🛒 어디서(공식 행사 페이지 링크) · 💸 할인 방식(쿠폰 · 즉시 할인 · 카드) · 🧾 조건(최소 금액 · 배송) · ⚠️ 주의.
- 할인율 · 가격은 공식 행사 페이지 · 보도자료로 확인된 것만. 작년 숫자는 '작년'이라고 밝힌다. 공식 발표 전이면 맨 위에 '○월 ○일 기준 공식 발표 없음'.
- 제휴 링크는 실제 제휴 링크가 있을 때만, 대가 문구는 첫 부분.

""" + FIGURES.format(prefix="IT할인", theme="it_sale · 주황")

# (사이트 카테고리 이름, 글 분류 기호, 방향, 독자의 질문, 컨셉, 소제목 빨간 막대)
ROUNDUPS = [
    ("무료 AI 툴", "B", "용도별로 돈 안 내고 쓸 수 있는 AI와 그 무료 범위를 한 편에",
     "무료로 쓸 수 있는 AI 뭐가 있고 어디까지 되지", TOOL, False),
    ("이달의 AI", "C", "한 달 동안 바뀐 AI를 날짜순으로 묶고, 가장 큰 변화와 내가 바꿀 것을 짚는다",
     "이번 달 AI 뭐가 바뀌었지", MONTH, True),
    ("IT 할인", "D", "광군제·블프·스팀 세일처럼 날짜가 정해진 IT 할인 행사를 한 편에, 언제 무엇을 살지",
     "IT 기기·프로그램 언제 사야 싸지", SALE, False),
]

ANIME_MARK = "분기 신작 글 (2026-10-31 사용자)"
ANIME_LINE = (ANIME_MARK + ": 환산기 짜임이 아니라 사용자가 쓰는 애니 글처럼 평범하게 — 작품마다 소제목 · 공식 키비주얼 1장 · "
              "방영일 · 어디서 보나(라프텔 · 넷플릭스 등) · 짧은 소개. 정리 그림(정리카드)은 쓰지 않는다. "
              "제목에는 '분기'를 넣는다 (구글에서 '분기 애니'가 '신작 애니'보다 많이 찾는다).")


def forward(apps, schema_editor):
    Blog = apps.get_model("blog_rules", "Blog")
    Section = apps.get_model("blog_types", "Section")
    Category = apps.get_model("blog_types", "Category")
    SiteCategory = apps.get_model("blog_types", "SiteCategory")

    section = Section.objects.filter(name="memorily", deleted_at__isnull=True).first()
    blog = Blog.objects.filter(name="memorily", deleted_at__isnull=True).first()
    for name, code, direction, question, concept, bar in ROUNDUPS:
        if section and not Category.objects.filter(section=section, name=name, deleted_at__isnull=True).exists():
            order = max(Category.objects.filter(section=section, deleted_at__isnull=True).values_list("order", flat=True), default=0) + 1
            Category.objects.create(section=section, code=code, name=name, order=order, direction=direction, question=question)
        if blog is None:
            continue
        cat = SiteCategory.objects.filter(blog=blog, parent__isnull=True, name=name, deleted_at__isnull=True).first()
        if cat is None:
            order = max(SiteCategory.objects.filter(blog=blog, parent__isnull=True, deleted_at__isnull=True)
                        .values_list("order", flat=True), default=0) + 1
            cat = SiteCategory.objects.create(blog=blog, name=name, order=order)
        if not cat.concept.strip():
            cat.concept = concept
            cat.heading_bar = bar
            cat.save(update_fields=["concept", "heading_bar"])

    anime = blog and SiteCategory.objects.filter(blog=blog, name__startswith="애니", deleted_at__isnull=True).order_by("pk").first()
    if anime and ANIME_MARK not in anime.concept:
        anime.concept = f"{anime.concept.rstrip()}\n\n{ANIME_LINE}" if anime.concept.strip() else ANIME_LINE
        anime.save(update_fields=["concept"])


class Migration(migrations.Migration):
    dependencies = [
        ("blog_types", "0051_local_lunch_cafe"),
        ("blog_rules", "0009_site_targets"),
        ("anime", "0003_memorily_anime_concept"),
    ]
    operations = [migrations.RunPython(forward, migrations.RunPython.noop)]
