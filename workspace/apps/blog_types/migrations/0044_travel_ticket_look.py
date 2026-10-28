"""워드프레스 › Korea Travel · World Travel 글 모양을 '주황 티켓'으로 (2026-10-28 사용자: "day head · time table 이 ppt 기본
디자인 같다" → 미리캔버스 '주황 심플 이탈리아 여행'의 디테일 — 도안을 고르고 "적용하고 글쓰기·변환 프롬프트도 꼼꼼히").

모양은 변환(wp_looks · 글모양.css)이 그린다. 컨셉에는 그 모양이 나오게 원고를 어떻게 쓰는지만 적는다:
이동 카드 이름은 'A → B', FAQ 는 '### 질문 + 답', 체크리스트는 '- [ ]'. 이미 있으면 건드리지 않는다. 지우는 데이터 없음.
"""
from django.db import migrations

MARK = "글 모양 (주황 티켓"
SWAPS = [
    ("FAQ 3~5개.", "FAQ 3~5개 (`### 질문` + 답 한두 문장)."),
    ("+ `::: Route` →", "+ `::: Route | {출발} → {도착}` →"),
    ("(`::: Route`)", "(`::: Route | {출발} → {도착}`)"),
    ("`## Entry & Money Checklist` (비자", "`## Entry & Money Checklist` (`- [ ]` 목록 — 비자"),
]
LINE = ("- 글 모양 (주황 티켓, 2026-10-28 사용자: 미리캔버스 '주황 심플 이탈리아 여행'의 디테일): 변환이 그린다 — 원고는 마크다운 그대로. "
        "소제목 위에 ✈ 01 번호, `## Day 1 · {지역}` 은 탑승권 머리(DAY 01 + 지역; `## Day 1 · Friday 6 Nov: {지역}` 처럼 쓰면 날짜는 작은 줄), "
        "첫 칸이 Time 인 시간 표는 점선 타임라인(칸은 Time | Stop | Time there | Move 그대로, 빈 칸은 —), "
        "`::: Route | A → B` 는 카드 안에 A ····✈···· B 경로선(꼭 → 로, 'to' 로 쓰면 경로선이 안 나온다, 괄호 설명은 선에서 빠진다), "
        "정보 카드는 각진 탭 라벨 + 선 아이콘(줄 머리 이모지는 화면에서 빠지니 이름표만으로 뜻이 통하게), "
        "FAQ 는 `### 질문` + 답 문단 → 질문 탭 + 답 판, 체크리스트는 `- [ ]` 목록 → 체크 목록. 꾸밈 코드·HTML 은 쓰지 않는다.")


def forward(apps, schema_editor):
    SiteCategory = apps.get_model("blog_types", "SiteCategory")
    for cat in SiteCategory.objects.filter(deleted_at__isnull=True, parent=None, blog__platform="wordpress",
                                           name__in=["Korea Travel", "World Travel"]):
        if MARK in cat.concept:
            continue
        concept = cat.concept
        for old, new in SWAPS:
            concept = concept.replace(old, new, 1)
        cat.concept = (concept.rstrip() + "\n" + LINE).strip()
        cat.save(update_fields=["concept"])


class Migration(migrations.Migration):
    dependencies = [("blog_types", "0043_bambam_travel_yudi")]
    operations = [migrations.RunPython(forward, migrations.RunPython.noop)]
