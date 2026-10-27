"""해외여행 글 맨 위에 위치 지도 (2026-10-27 사용자: "나는 사실 어딘지도 몰라 너가 쓰는 지역들이").

밤밤 › 해외여행 · 워드프레스 › World Travel 컨셉에 '위치 지도' 줄을 더한다. 변환 요청문은 컨셉에 '위치 지도'가 있으면
그리는 법(site_templates.prompt.LOCATOR)을 붙인다. 이미 있으면 건드리지 않는다. 지우는 데이터 없음.
"""
from django.db import migrations

LINE = ("- 위치 지도: 맨 위 인용 바로 다음(대표 사진이 있으면 그 다음)에 그 도시 위치 지도 1장 — 가공이미지, 변환이 그린다 "
        "(2026-10-27 사용자: 어디인지 감이 안 온다).")
WP_ORDER = ("순서: 리드 → `## Trip at a Glance`", "순서: 리드 → 위치 지도 → `## Trip at a Glance`")


def forward(apps, schema_editor):
    SiteCategory = apps.get_model("blog_types", "SiteCategory")
    targets = SiteCategory.objects.filter(deleted_at__isnull=True, parent=None).filter(
        blog__name="밤밤", name="해외여행") | SiteCategory.objects.filter(
        deleted_at__isnull=True, parent=None, blog__platform="wordpress", name="World Travel")
    for cat in targets:
        if "위치 지도" in cat.concept:
            continue
        cat.concept = cat.concept.replace(*WP_ORDER, 1)
        cat.concept = (cat.concept.rstrip() + "\n" + LINE).strip()
        cat.save(update_fields=["concept"])


class Migration(migrations.Migration):
    dependencies = [("blog_types", "0036_car_topics_wide")]
    operations = [migrations.RunPython(forward, migrations.RunPython.noop)]
