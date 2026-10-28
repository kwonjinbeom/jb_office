"""사이트별 템플릿 › 카테고리의 디자인 컨셉 (2026-10-28 사용자: 그 카테고리 글에 쓰는 표·메모·소제목·색을 한곳에).

견본은 손으로 그리지 않는다. 요소마다 짧은 마크다운을 변환과 같은 코드(views._render_cat)로 그린다 —
글 모양(looks · wp_looks · writing.render)을 고치면 견본도 저절로 따라온다. 색은 화면이 그려진 견본을 읽어 모은다
(templates/site_templates/index.html 스크립트).
"""
from apps.blog_rules.models import Blog
from apps.writing.render import CARD_KINDS

# 정보 카드 종류: 그 글 모양의 카테고리 컨셉이 쓰는 것 (wp_looks.PROMPT · 글모양.css 의 테마별 카드)
WP_KINDS = {
    "wp_mountain": ["요약", "코스", "캠핑", "비용", "나들이"],
    "wp_car": ["요약", "차", "비용", "점검"],
    "wp_travel": ["Place", "Food", "Stay", "Route", "Cost", "Info"],
}
ENGLISH = {"wp_travel"}  # Korea Travel · World Travel 은 영어 글


# 견본 사진 (static/img): 본문 정리가 http 주소 그림만 남기므로 views 가 절대 주소로 바꿔 넣는다
PHOTO_A, PHOTO_B = "{photo_a}", "{photo_b}"
PHOTOS = {"photo_a": "img/design-sample-a.svg", "photo_b": "img/design-sample-b.svg"}

KO = {
    "heading": ("소제목", "## 소제목 · ### 작은 소제목",
                "## 1. 어디부터 볼까요?\n\n소제목 아래 본문 한 줄.\n\n### 작은 소제목\n\n작은 소제목 아래 본문 한 줄."),
    "text": ("문단·강조", "**굵게** · [링크](주소) · - 목록",
             "보통 문단은 이렇게 보여요. **꼭 짚을 말**은 굵게, [링크](https://example.com)는 이렇게.\n\n- 목록 첫째\n- 목록 둘째"),
    "lead": ("맨 위 인용", "> 2~3줄 요약", "> 이 글이 무엇을 다루는지 두세 줄로.\n> 다 읽으면 무엇을 알게 되는지."),
    "table": ("표", "| 머리 | 칸 |",
              "| 항목 | 내용 | 비고 |\n|---|---|---|\n| 시간 | 09:00~18:00 | 월요일 휴무 |\n| 요금 | 5,000원 | 어린이 반값 |"),
    "card": ("정보 카드", "::: 종류 | 이름 … :::", ""),
    "photo": ("사진", "![설명](주소) + *사진: 출처*", f"![견본 사진]({PHOTO_A})\n*사진: 작가 · 출처*"),
    "hr": ("나눔표", "---", "앞 단락의 마지막 줄.\n\n---\n\n다음 단락의 첫 줄."),
    "toc": ("목차", "## 소제목 4개 이상이면 저절로",
            "## 가는 길\n\n한 줄.\n\n## 볼거리\n\n한 줄.\n\n## 먹을 곳\n\n한 줄.\n\n## 정리\n\n한 줄."),
    "day": ("날짜 머리", "## 1일차 · 지역", "## 1일차 · 교토 동쪽\n\n그날 일정 한 줄."),
    "source": ("출처 줄", "참고: 출처", "본문 마지막 줄.\n\n참고: [기관 누리집](https://example.com) · [안내 문서](https://example.com)"),
}
EN = {
    **KO,
    "heading": ("소제목", "## 소제목 · ### 작은 소제목",
                "## Getting There\n\nOne line under the heading.\n\n### Small heading\n\nOne line under the small heading."),
    "text": ("문단·강조", "**굵게** · [링크](주소) · - 목록",
             "A plain paragraph looks like this. **Key words** in bold, [a link](https://example.com) like this.\n\n- First item\n- Second item"),
    "lead": ("맨 위 인용", "> 2~3줄 요약", "> What this post covers, in two or three lines.\n> What you will know by the end."),
    "table": ("표", "| 머리 | 칸 |",
              "| Item | Detail | Note |\n|---|---|---|\n| Hours | 9am–6pm | Closed Mon |\n| Price | ₩5,000 | Kids half |"),
    "photo": ("사진", "![설명](주소) + *Photo: 출처*", f"![Sample photo]({PHOTO_A})\n*Photo: Author · Source*"),
    "hr": ("나눔표", "---", "Last line of a section.\n\n---\n\nFirst line of the next."),
    "toc": ("목차", "## 소제목 4개 이상이면 저절로",
            "## Getting There\n\nOne line.\n\n## What to See\n\nOne line.\n\n## Where to Eat\n\nOne line.\n\n## Tips\n\nOne line."),
    "day": ("날짜 머리", "## Day 1 · 지역", "## Day 1 · Eastern Kyoto\n\nOne line for the day."),
    "lang": ("다른 언어 요약", "## 日本語まとめ · ## 中文简介",
             "## 日本語まとめ\n\n短い要約を二、三行で。\n\n## 中文简介\n\n用两三行简单介绍。"),
    "source": ("출처 줄", "Sources: 출처", "Last line of the post.\n\nSources: [Official site](https://example.com) · [Guide](https://example.com)"),
}
ROWS_KO = "📍 주소 | 서울 종로구 사직로 161\n⏰ 시간 | 09:00~18:00\n💰 요금 | 3,000원"
ROWS_EN = "📍 Address | 161 Sajik-ro, Jongno-gu, Seoul\n⏰ Hours | 9am–6pm\n💰 Price | ₩3,000"


def _cards(kinds, english=False):
    name, rows = ("Sample", ROWS_EN) if english else ("견본", ROWS_KO)
    return "\n\n".join(f"::: {k} | {name} {k}\n{rows}\n:::" for k in kinds)


def items(platform, look, heading_bar=False, photos=None):
    """그 카테고리 글에 나오는 요소 (이름, 쓰는 법, 견본 마크다운) — 화면에 나오는 순서대로. photos: PHOTOS 의 절대 주소"""
    wp = platform == Blog.Platform.WORDPRESS
    english = look in ENGLISH
    src = EN if english else KO
    out = {k: list(v) for k, v in src.items()}
    if heading_bar:
        out["heading"][0] = "소제목 (빨간 막대)"
    if look == "yudi":
        out["text"][1] += " · ==형광펜=="
        out["text"][2] += "\n\n가장 중요한 한 구절은 ==형광펜==으로."
        out["card"] = ["메모지 상자", "::: 장소 | 이름 … :::", _cards(["장소"])]
        out["photo"] = ["사진 콜라주", "사진 2장 이상 연달아",
                        f"![견본 사진]({PHOTO_A})\n*사진: 작가 · 출처*\n\n![견본 사진]({PHOTO_B})\n*사진: 작가 · 출처*"]
    elif wp:
        kinds = WP_KINDS.get(look, ["요약", "장소", "맛집"])
        out["card"][2] = _cards(kinds, english)
    else:
        out["card"][2] = _cards(list(CARD_KINDS))
        out["table"][1] += " · 🔥 줄"
        out["table"][2] += "\n| 🔥 강조 줄 | 🔥 로 시작하면 | 줄 전체에 바탕색 |"
    keys = ["heading", "text", "lead", "table", "card", "photo", "hr", "source"]
    if wp:
        keys[3:3] = ["toc"]
        if look == "wp_travel":
            keys += ["day", "lang"]
    photos = photos or {k: "https://example.com/" + v for k, v in PHOTOS.items()}
    return [{"key": k, "name": out[k][0], "how": out[k][1], "md": out[k][2].format(**photos) if k == "photo" else out[k][2]}
            for k in keys]
