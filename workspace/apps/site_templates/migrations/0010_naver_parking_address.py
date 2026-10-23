"""2026-10-23 사용자: 주차장 지도 링크도 📍 주소처럼 — 이름은 글로 두고 주소 글자에 지도 링크. 도로명이 없으면 지번.

1. black_lukey 사이트 템플릿 '꼭 지킬 것'에 한 줄 (이미 있으면 그대로).
2. 지역 놀거리 · 축제·행사 컨셉의 🅿️ 주차 설명을 바꾼다 (그 글이 있을 때만 — 사용자가 고친 컨셉은 건드리지 않는다).
같은 규칙이 원고 체크리스트(일일루틴/프롬프트/writing_checklist.md)에도 있다.
"""
from django.db import migrations

RULE = ("🅿️ 주차도 📍 주소와 같다: `🅿️ 주차 | 주차장 이름 [주소](https://map.naver.com/p/entry/place/<번호>) 요금` — "
        "이름은 글로 두고 주소 글자에 지도 링크, '[네이버 지도]' 로 쓰지 않는다. 도로명이 없으면 지번 주소.")
SWAPS = [("🅿️ 주차(주차장 이름·요금 + 네이버 지도 링크)", "🅿️ 주차(주차장 이름 + 주소 글자에 네이버 지도 링크 · 요금)")]
CATEGORIES = ("지역 놀거리", "축제·행사")


def forward(apps, schema_editor):
    SiteTemplate = apps.get_model("site_templates", "SiteTemplate")
    SiteCategory = apps.get_model("blog_types", "SiteCategory")
    for tpl in SiteTemplate.objects.filter(blog__name="black_lukey"):
        if RULE not in tpl.rules:
            tpl.rules = "\n".join([tpl.rules.rstrip(), RULE]).strip()
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
        rules = "\n".join(line for line in tpl.rules.split("\n") if line != RULE)
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
    dependencies = [("site_templates", "0009_naver_address_links")]
    operations = [migrations.RunPython(forward, backward)]
