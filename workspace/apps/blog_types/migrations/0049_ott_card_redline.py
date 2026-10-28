"""black_lukey › 영화·OTT 공개 작품 카드를 'B 레드 라인'으로 (2026-10-28 사용자: 예시안에서 B 를 고르고 "앞으로 쓰는 글들에 적용할테니
관련 프롬프트에 정리해줘"). 그리는 것은 site_templates.red_look 이 하고, 여기서는 컨셉의 '화면 모양' 묶음 끝에 카드 한 줄을 더한다.
이미 있으면 건드리지 않는다. 지우는 데이터 없음. 되돌리면 그 줄만 뺀다.
"""
from django.db import migrations

NAME = "영화·OTT 공개"
MARK = "작품 카드 (레드 라인"
LINE = ("- 작품 카드 (레드 라인, 2026-10-28 사용자): 머리 줄은 흰 바탕에 빨간 윗줄·검정 아랫줄('작품 정보'만 빨강, 작품 이름은 검정 굵게), "
        "몸은 연회색 이름표 칸에 검정 글자 · 이름표와 값 사이 세로 줄 · 맨 아래 검정 줄. 변환이 그린다 — 원고는 `::: 작품 | 제목` 과 "
        "`이모지 이름표 | 값` 줄 그대로 (이모지를 빼지 않는다).")


def forward(apps, schema_editor):
    SiteCategory = apps.get_model("blog_types", "SiteCategory")
    for cat in SiteCategory.objects.filter(blog__platform="naver", name=NAME, parent=None, deleted_at__isnull=True):
        if MARK not in cat.concept:
            cat.concept = (cat.concept.rstrip() + "\n" + LINE).strip()
            cat.save(update_fields=["concept"])


def backward(apps, schema_editor):
    SiteCategory = apps.get_model("blog_types", "SiteCategory")
    for cat in SiteCategory.objects.filter(blog__platform="naver", name=NAME, parent=None, deleted_at__isnull=True):
        if LINE in cat.concept:
            cat.concept = cat.concept.replace("\n" + LINE, "").replace(LINE, "").strip()
            cat.save(update_fields=["concept"])


class Migration(migrations.Migration):
    dependencies = [("blog_types", "0048_wordpress_drop_asof_line")]
    operations = [migrations.RunPython(forward, backward)]
