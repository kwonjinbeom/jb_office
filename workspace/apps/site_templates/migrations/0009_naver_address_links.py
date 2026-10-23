"""2026-10-23 사용자 피드백 (네이버 black_lukey): 정보 카드의 📍 줄은 도로명 주소에 네이버 지도 링크, 맨 위 첫 요약은 짧은 문장.

1. black_lukey 사이트 템플릿 '꼭 지킬 것'에 두 줄을 더한다 (이미 있으면 그대로).
2. 지역 놀거리 · 축제·행사 컨셉의 '📍 지도' 를 '📍 주소' 로 (그 글이 있을 때만 바꾼다 — 사용자가 고친 컨셉은 건드리지 않는다).
같은 규칙이 원고 체크리스트(일일루틴/프롬프트/writing_checklist.md)에도 있다. 영화명 세로줄·첫 요약 줄바꿈은 그릴 때 한다 (naver_writing.render).
"""
from django.db import migrations

RULES = [
    "정보 카드의 📍 줄은 `📍 주소 | [도로명 주소](https://map.naver.com/p/entry/place/<번호>)` — 링크 글은 '네이버 지도'가 아니라 그 장소의 도로명 주소 "
    "(예: [강원 강릉시 용지로 176](https://map.naver.com/p/entry/place/1657248154)). 주소는 https://map.naver.com/p/api/place/summary/<번호> 의 roadAddress.",
    "맨 위 인용 상자(첫 요약)는 짧은 문장 2~3개. 한 문장에 여러 정보를 쉼표로 길게 잇지 않는다 (서버가 문장마다 줄을 바꾼다).",
]
SWAPS = [  # (예전 글, 새 글) — 카테고리 컨셉 (site_templates 0008 의 글)
    ("📍 지도(네이버 지도 장소 링크)", "📍 주소(도로명 주소 글에 네이버 지도 장소 링크)"),
    ("⏰ 영업·휴무 · 📍 지도)", "⏰ 영업·휴무 · 📍 주소)"),
    ("- 지도: 모든 갈 곳에 네이버 지도 장소 링크.", "- 지도: 모든 갈 곳에 📍 주소 줄 (도로명 주소 글에 네이버 지도 장소 링크)."),
]
CATEGORIES = ("지역 놀거리", "축제·행사")


def forward(apps, schema_editor):
    SiteTemplate = apps.get_model("site_templates", "SiteTemplate")
    SiteCategory = apps.get_model("blog_types", "SiteCategory")
    for tpl in SiteTemplate.objects.filter(blog__name="black_lukey"):
        add = [line for line in RULES if line not in tpl.rules]
        if add:
            tpl.rules = "\n".join([tpl.rules.rstrip(), *add]).strip()
            tpl.save(update_fields=["rules"])
    for cat in SiteCategory.objects.filter(blog__name="black_lukey", name__in=CATEGORIES):
        concept = cat.concept
        for old, new in SWAPS:
            concept = concept.replace(old, new)
        if concept != cat.concept:
            SiteCategory.objects.filter(pk=cat.pk).update(concept=concept)


def backward(apps, schema_editor):
    SiteTemplate = apps.get_model("site_templates", "SiteTemplate")
    SiteCategory = apps.get_model("blog_types", "SiteCategory")
    for tpl in SiteTemplate.objects.filter(blog__name="black_lukey"):
        rules = "\n".join(line for line in tpl.rules.split("\n") if line not in RULES)
        if rules != tpl.rules:
            tpl.rules = rules
            tpl.save(update_fields=["rules"])
    for cat in SiteCategory.objects.filter(blog__name="black_lukey", name__in=CATEGORIES):
        concept = cat.concept
        for old, new in SWAPS:
            concept = concept.replace(new, old)
        if concept != cat.concept:
            SiteCategory.objects.filter(pk=cat.pk).update(concept=concept)


class Migration(migrations.Migration):
    dependencies = [("site_templates", "0008_black_lukey_categories")]
    operations = [migrations.RunPython(forward, backward)]
