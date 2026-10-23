"""눈잎 › 일상도 일본 여행과 같은 '유디 메모지' 글 모양 (2026-10-23 사용자).

사용자: 일상에는 대부분 제품 소개가 들어간다. 여행지 형태가 아니라 일본 여행에서 쓴 테마·구조·CSS 전체를 그대로 — 공모주·정책은 그대로 둔다.
1. 사이트 카테고리 눈잎 › 일상: 글 모양(look) = yudi, 컨셉 = 제품 소개 짜임새 + 화면 모양 (기본 컨셉이면 바꾸고, 직접 쓴 컨셉이면 뒤에 덧붙인다).
2. 지금 일상에 넣은, 아직 발행 안 한 글(변환을 마친 것)은 '변환 요청'으로 돌리고 '이 글만'에 새 모양으로 다시 맞추라고 적는다
   → 발행예정글의 '다시' 버튼 한 번이면 PC 터미널이 새 컨셉·모양으로 다시 변환한다. 지우는 데이터 없음 (지난 변환본은 다시 받을 때까지 그대로).
"""
from django.db import migrations

OLD = "사용자가 직접 쓰는 일상 글"

SHAPE = "\n".join([
    "제품 소개 글 모양 (일본 여행과 같은 짜임 — 무엇을·왜·누구에게가 한눈에 맞아떨어져야 한다):",
    "- 한 편에 제품 하나, 또는 같은 쓰임의 제품 2~5개 비교. 소개·비교·고르는 법 글을 돌린다.",
    "- 순서: 맨 위 인용(누구에게 · 무엇이 좋은지 · 값 한 줄) → 목차 → 한눈에 보는 표(제품 · 가격 · 핵심 한 줄 · 맞는 사람) → "
    "제품마다(또는 쓰는 장면마다) → 고르는 법·비교 → 마무리.",
    "- 제품마다: `## 번호. 짧은 물음` → `### 제품 이름` → 사진 2~4장(제품·쓰는 장면, 공식 제품 사진 가능) → 서술 2~4문장(무엇이 다른지 · 어떤 때 좋은지) → "
    "정보 카드 `::: 제품 | 정식 이름` (💰 가격(기준일) · 📦 구성·용량 · ✨ 특징 · 👍 맞는 사람 · ⚠️ 알아 둘 점 · 🛒 사는 곳 링크).",
    "- 가격은 확인한 날짜와 함께, 바뀔 수 있음을 한 줄. 대가성(제휴·협찬)이 있으면 맨 위에 표기한다.",
    "- 써 본 척하지 않는다 (\"써 보니\", \"샀는데\"). 사용자가 직접 쓴 경험은 그대로 살린다. 써 본 사람들의 후기는 '써 본 사람들은 …'으로, 출처를 단다.",
    "- 마무리: 표·목록 없이 서술 2~4문장 — 어떤 사람에게 무엇을 고르면 좋은지. 상투어 금지.",
])

LOOK = "\n".join([
    "화면 모양 (유디 블로그의 화면 짜임 — 눈잎 › 일본 여행과 같다, 붙여 넣는 HTML 이 그린다 · 변환본에는 꾸밈 코드를 넣지 않는다):",
    "- 가운데 정렬, 한 줄에 한 호흡 (짧게 끊어 줄바꿈, 2~4줄이 한 단락, 단락 사이 넉넉히).",
    "- 나눔스퀘어 본문, 굵게는 청록 굵은 글자 · 가장 중요한 한 구절은 연두 형광펜(==…==).",
    "- 소제목은 코랄 큰따옴표 + 둥근 굵은 글씨 + 연두 형광펜 밑칠 (번호 단 짧은 물음), 큰 단락 사이 가운데 나눔표(---).",
    "- 정보는 모서리 접힌 메모지 상자(청록 글자) · 목차는 가운데 좁은 표(머리 칸 연두) · 맨 위 인용은 연한 청록 둥근 상자 · 사진은 2장씩 콜라주, 둥근 모서리.",
])

CONCEPT = "일상 속 제품을 소개한다 (생활용품·가전·계절템 등). 사용자가 직접 쓴 일상 글도 이 카테고리.\n\n" + SHAPE + "\n\n" + LOOK

NOTE = ("글 모양을 눈잎 › 일본 여행과 같은 유디 메모지로 다시 맞춘다 (2026-10-23 사용자): 카테고리 컨셉의 '제품 소개 글 모양'·'화면 모양'과 "
        "요청문의 '글 모양 — 유디 메모지'대로 — 한 줄에 한 호흡, 번호 단 짧은 물음 소제목, 제품마다 ### 이름 · 사진 2장 이상 · ::: 제품 카드. "
        "내용·사실은 지난 변환본을 살린다.")


def forward(apps, schema_editor):
    SiteCategory = apps.get_model("blog_types", "SiteCategory")
    Placement = apps.get_model("blog_types", "Placement")
    for cat in SiteCategory.objects.filter(blog__name="눈잎", name="일상", parent__isnull=True, deleted_at__isnull=True):
        if cat.concept.strip() in ("", OLD):
            cat.concept = CONCEPT
        elif "화면 모양" not in cat.concept:
            cat.concept = cat.concept.rstrip() + "\n\n" + SHAPE + "\n\n" + LOOK
        cat.look = "yudi"
        cat.save(update_fields=["concept", "look"])
        for pl in Placement.objects.filter(site_category__in=[cat, *cat.children.all()], status="unsaved",
                                           convert_status__in=["done", "checked"], deleted_at__isnull=True):
            pl.convert_status = "requested"
            pl.convert_note = (NOTE + ("\n" + pl.convert_note if pl.convert_note else ""))[:300]
            pl.save(update_fields=["convert_status", "convert_note"])


class Migration(migrations.Migration):
    dependencies = [("blog_types", "0024_nunip_japan_concept_general")]
    operations = [migrations.RunPython(forward, migrations.RunPython.noop)]
