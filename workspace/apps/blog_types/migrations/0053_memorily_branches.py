"""memorily 컨셉 갈래 (2026-10-31 사용자: AI 카테고리를 IT·AI 로 바꿨다. 총정리 글도 다 거기 올린다 —
블로그 메뉴는 하나지만 템플릿 컨셉은 다르니 갈라 두고, 볼 때 헷갈리지 않게 표기를 다르게. 애니도 계층으로 둘).

1. SiteCategory.branch '컨셉 갈래': 블로그에는 없는 하위 카테고리. 글은 위 카테고리에 올리고 변환만 이 컨셉을 더 받는다.
   화면에서는 'IT·AI (컨셉: 무료 AI 툴)' 로 적는다.
2. memorily › AI → IT·AI (이미 바꿨으면 그대로). 그 아래 갈래 넷: AI 소식(옛 AI 컨셉 · 빨간 막대) · 무료 AI 툴 · 이달의 AI · IT 할인
   (0052 가 맨 위에 만든 셋을 옮긴다). IT·AI 자체는 짧은 안내만. AI 소식 글의 넣은 곳은 AI 소식 갈래로.
3. memorily › 애니 아래 갈래 둘: 회차정리(옛 애니 컨셉) · 분기 신작. 애니 글의 넣은 곳은 회차정리로.
4. 총정리 세 갈래의 그림: PT 식 정리카드(0052)를 버리고 주제 그림 — 주제를 장면으로 그린 일러스트 (변환그림/주제그림.py,
   사용자: "견본은 그 주제를 이미지화했다. 이건 평소 하던 글 정리다"). 0052 값 그대로일 때만 바꾼다.
같은 글이 작가 파일(일일루틴/프롬프트/writing_site_memorily.md)에도 있다 — 고칠 때 둘 다. 지우는 데이터 없음.
"""
import re
from importlib import import_module

from django.db import migrations, models

OLD = import_module("apps.blog_types.migrations.0052_memorily_roundups")

IT_AI = "IT·AI"
IT_AI_NOTE = ("IT·AI (2026-10-31 사용자, 옛 이름 AI): 블로그 메뉴는 이것 하나다. 글 모양은 컨셉 갈래 — AI 소식 · 무료 AI 툴 · 이달의 AI · "
              "IT 할인 — 마다 따로 있고, 넣은 곳의 갈래 컨셉을 따른다.")
ANIME_NOTE = ("애니 (2026-10-31 사용자): 블로그 메뉴는 이것 하나다. 글 모양은 컨셉 갈래 — 회차정리 · 분기 신작 — 마다 따로 있고, "
              "넣은 곳의 갈래 컨셉을 따른다.")
SEASON = ("분기 신작 (2026-10-31 사용자): 환산기 짜임이 아니라 사용자가 쓰는 애니 글처럼 평범하게 — 작품마다 소제목 · 공식 키비주얼 1장 · "
          "방영일 · 어디서 보나(라프텔 · 넷플릭스 등) · 짧은 소개. 주제 그림은 쓰지 않는다. 제목에 '분기'를 넣는다 "
          "(구글에서 '분기 애니'가 '신작 애니'보다 많이 찾는다). 방영작은 공식 발표로 확인하고 확정 · 예정을 나눠 적는다.")

FIGURES = """주제 그림 (가공이미지, 2026-10-31 사용자 — 예시 dhsy.tistory.com/420 처럼 그 주제를 그림으로. 표를 옮긴 PT 식 그림은 쓰지 않는다):
- `python 콘텐츠/블로그_카페/변환그림/주제그림.py <설계 json> 콘텐츠/블로그_카페/변환그림/<글 번호>/<이름>.png` 로 그린다 (theme {theme}).
  견본 설계는 `변환그림/주제그림_견본/{prefix}_*.json` — 모양만 따르고 제목 · 날짜 · 숫자는 이 글의 것으로.
- 표지(kind cover) 1장 — 맨 위 인용 바로 다음, 이 글의 대표 그림: {cover} 장면 + 큰 제목(포인트 말은 *말*) + 한 줄 설명.
- 섹션(kind section) 1~2장 — 둘을 견주는 곳에: 칸마다 작은 장면 + 정보 3~4줄 + 한 줄 메모. 장면: {scenes}.
- 그림 속 날짜 · 숫자는 사실 점검을 마친 것만. 실제 사진(공식 화면 · 보도 이미지 · 제품 실물)은 그림과 따로 넣는다."""

TOOL = """무료 AI 툴: 용도(이미지 · 영상 · PPT · 글쓰기 · 코딩 · 음성 …)마다 돈 안 내고 어디까지 되는지 총정리. 결론 먼저, 확인된 것 위주로 담백하게.
글 모양 (black_lukey › 출시의 짜임을 이 소재에 맞게):
- 순서: 맨 위 인용(결론 2~3문장: 이 용도면 무엇 · 무료 범위 한 줄) → 표지 그림 → 한눈에 표(툴 · 무료로 되는 것 · 무료 한도 · 한국어 · 상업 이용 · 가입) → 툴마다 소제목 → 섹션 그림(두 용도 · 두 툴 견주기) → 무료로 쓸 때 주의(상업 이용 · 저작권 · 개인정보 · 워터마크) → 공식 요금 페이지 보는 곳 → 참고 줄.
- 툴마다 `## 툴 이름 — 한 줄 포인트`: 실제 화면 사진 1장(공식 화면 · 보도 이미지, 또는 직접 연 화면 캡처 — 로그인 정보 · 개인 정보가 보이지 않게) → 서술 2~3문장(무엇을 잘하나 · 무료에서 막히는 곳) → `::: 제품 | 툴 이름` 카드: 💳 무료 범위 · 💰 유료 요금(월, 원화) · 🇰🇷 한국어 · 🧾 상업 이용 · 🔑 가입 · 🔗 바로가기(공식 주소).
- 무료 범위는 자주 바뀐다: 표 아래에 '○월 ○일 각 서비스 요금 페이지 기준' 한 줄. 확인 못 한 한도는 쓰지 않는다.
- 써 본 척하지 않는다. 다른 사람 후기는 '써 본 사람들은 …' + 출처.

""" + FIGURES.format(theme="ai_tool · 청록", prefix="무료AI툴", cover="노트북에서 이미지 · 영상 · PPT · 문서 창이 떠오르는 책상",
                     scenes="image · video · slides · writing · code · voice")

MONTH = """이달의 AI: 한 달 동안 바뀐 AI를 한 편에 (매월 1~3일, 지난달). 재료는 그달 AI 소식 원고와 공식 발표.
날마다 쓴 AI 소식을 그대로 옮기지 않고, 한 달을 묶어 '무엇이 가장 컸나 · 나는 뭘 바꾸면 되나'로.
글 모양 (black_lukey › 출시의 짜임을 이 소재에 맞게):
- 순서: 맨 위 인용(이달 가장 큰 변화 2~3문장) → 표지 그림 → 날짜순 표(날짜 · 도구 · 바뀐 것 · 누구에게) → 도구마다 소제목 → 섹션 그림(가장 큰 변화 둘) → 확인된 것 · 소문 · 믿지 않아도 되는 것 → 다음 달 볼 것(발표 예정 · 요금 적용일) → 공식 소식 보는 곳 → 참고 줄.
- 도구마다 `## 도구 — 무엇이 바뀌었나`: 실제 사진 1장(공식 발표 이미지 · 제품 화면) → 2~4줄 → `::: 제품 | 도구 이름` 카드: 📅 발표 · 적용일 · 💳 대상 · 요금제 · 🇰🇷 한국 사용 · 🔗 공식 발표.
- 그달 AI 소식 글의 발행 주소가 있으면 그 항목 끝에 '자세히: ○월 ○일 AI 소식' 링크.
- 소제목: 앞의 빨간 세로 막대는 붙여넣는 HTML 이 단다 (AI 소식과 같다).

""" + FIGURES.format(theme="ai_month · 빨강 #e03131", prefix="이달의AI", cover="큰 달력 + 겹쳐 뜬 AI 창 + 로봇 (label 에 '11월')",
                     scenes="chat · bot · calendar · code · image")

SALE = """IT 할인: 광군제 · 블랙프라이데이 · 사이버먼데이 · 스팀 세일처럼 날짜가 정해진 IT 할인 행사를 한 편에 (행사 7~10일 전).
기기 · 주변기기 · 소프트웨어 · 게임만 — 옷 · 화장품은 다루지 않는다. 기기 한 대 · 게임 한 편의 출시는 black_lukey › 출시가 쓴다.
글 모양 (black_lukey › 출시의 짜임: 결론 → 일정 표 → 알려진 것 → 살까 기다릴까 → 공식 소식):
- 순서: 맨 위 인용(결론 2~3문장: 언제 무엇을 사면 좋은지) → 표지 그림 → 행사 일정 표(행사 · 기간(한국시간) · 어디서 · 잘 맞는 물건) → 행사마다 소제목 → 섹션 그림(행사 둘 견주기) → 지금 살까 기다릴까(물건 · 사기 좋은 때 · 까닭 표 + 서술) → 직구 체크(면세 한도 · 배송 기간 · 전압 · AS — 숫자는 관세청 공식 안내로) → 공식 소식 보는 곳 → 참고 줄.
- 행사마다 `## 행사 이름 · 기간`: 실제 사진 1~2장(행사 공식 페이지 화면 · 제품 실물) → 서술 2~3문장 → `::: 제품 | 행사 이름` 카드: 📅 기간(한국시간) · 🛒 어디서(공식 행사 페이지 링크) · 💸 할인 방식(쿠폰 · 즉시 할인 · 카드) · 🧾 조건(최소 금액 · 배송) · ⚠️ 주의.
- 할인율 · 가격은 공식 행사 페이지 · 보도자료로 확인된 것만. 작년 숫자는 '작년'이라고 밝힌다. 공식 발표 전이면 맨 위에 '○월 ○일 기준 공식 발표 없음'.
- 제휴 링크는 실제 제휴 링크가 있을 때만, 대가 문구는 첫 부분.

""" + FIGURES.format(theme="it_sale · 주황", prefix="IT할인", cover="할인 화면 노트북 · 택배 상자 · 쇼핑백 · 가격표 책상 (label 에 '11.11' 같은 날짜)",
                     scenes="parcel · laptop · keyboard · bag · tag · calendar")

# 갈래 이름: (0052 의 옛 컨셉, 새 컨셉)
ROUNDUPS = {"무료 AI 툴": (OLD.TOOL, TOOL), "이달의 AI": (OLD.MONTH, MONTH), "IT 할인": (OLD.SALE, SALE)}


def _bare(name):
    return re.sub(r"\s+", "", name or "")


def _branch(SiteCategory, top, name, order):
    """top 아래 name 갈래 — 맨 위에 같은 이름이 있으면(0052) 옮겨 온다."""
    cat = (SiteCategory.objects.filter(blog=top.blog, parent=top, name=name, deleted_at__isnull=True).first()
           or SiteCategory.objects.filter(blog=top.blog, parent__isnull=True, name=name, deleted_at__isnull=True).first()
           or SiteCategory(blog=top.blog, name=name))
    cat.parent, cat.branch, cat.order = top, True, order
    cat.save()
    return cat


def forward(apps, schema_editor):
    Blog = apps.get_model("blog_rules", "Blog")
    SiteCategory = apps.get_model("blog_types", "SiteCategory")
    Placement = apps.get_model("blog_types", "Placement")
    blog = Blog.objects.filter(name="memorily", deleted_at__isnull=True).first()
    if blog is None:
        return
    tops = SiteCategory.objects.filter(blog=blog, parent__isnull=True, deleted_at__isnull=True).order_by("pk")

    # IT·AI
    top = next((c for c in tops if _bare(c.name) == _bare(IT_AI)), None) or next((c for c in tops if c.name == "AI"), None)
    if top is not None:
        news = _branch(SiteCategory, top, "AI 소식", 1)
        if not news.concept.strip() and top.concept.strip() and top.concept.strip() != IT_AI_NOTE:
            news.concept = top.concept
        news.heading_bar = news.heading_bar or top.heading_bar
        news.save()
        top.name, top.concept, top.heading_bar = IT_AI, IT_AI_NOTE, False
        top.save()
        for order, (name, (old, new)) in enumerate(ROUNDUPS.items(), 2):
            cat = _branch(SiteCategory, top, name, order)
            if cat.concept.strip() in ("", old.strip()):
                cat.concept = new
                cat.save()
        Placement.objects.filter(site_category=top, tistory_post__title__contains="AI 소식").update(site_category=news)

    # 애니
    anime = next((c for c in tops if c.name.startswith("애니")), None)
    if anime is not None:
        episodes = _branch(SiteCategory, anime, "회차정리", 1)
        season = _branch(SiteCategory, anime, "분기 신작", 2)
        old = anime.concept.replace(OLD.ANIME_LINE, "").strip()
        if not episodes.concept.strip() and old and old != ANIME_NOTE:
            episodes.concept = old
            episodes.save()
        if not season.concept.strip():
            season.concept = SEASON
            season.save()
        anime.concept = ANIME_NOTE
        anime.save()
        Placement.objects.filter(site_category=anime).update(site_category=episodes)


class Migration(migrations.Migration):
    dependencies = [("blog_types", "0052_memorily_roundups")]
    operations = [
        migrations.AddField(
            model_name="sitecategory",
            name="branch",
            field=models.BooleanField(default=False, verbose_name="컨셉 갈래",
                                      help_text="블로그에는 없는 하위 카테고리 — 글은 위 카테고리에 올리고, 템플릿 컨셉만 따로 갖는다"),
        ),
        migrations.RunPython(forward, migrations.RunPython.noop),
    ]
