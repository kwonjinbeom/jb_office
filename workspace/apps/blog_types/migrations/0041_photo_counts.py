"""워드프레스 사진이 빠지지 않게 (2026-10-27 사용자: 선운산 글에 산 사진이 하나도 없다, 로마편도 사진이 없다 — 프롬프트를 고쳐 누락되지 않게).

산과 캠핑 · Korea Travel · World Travel 컨셉의 사진 줄에 장수(바닥)와 먼저 찾을 곳을 적는다.
사용자가 이미 고친 줄은 건드리지 않는다. 지우는 데이터 없음.
"""
from django.db import migrations

MOUNTAIN = ("- 사진: 그 산이 그 계절에 실제로 찍힌 무료 사진 2~4장.",
            "- 사진: 그 산이 그 계절에 실제로 찍힌 무료 사진 2~4장 — 꼭 (2026-10-27 사용자: 선운산 글에 사진이 하나도 없었다). "
            "국내 산은 한국관광콘텐츠랩 고품질사진(옛 포토코리아, 공공누리 제1유형)에 거의 다 있다: 맨 위 대표 1장 + 코스 지점(절·계곡·능선·정상) 1~3장. "
            "사진 없이 내지 않는다.")
TRAVEL = ("사진은 그 장소가 실제로 찍힌 무료 사진.",
          "사진은 그 장소가 실제로 찍힌 무료 사진 — 맨 위 대표 1장 + Day 마다 그날 주인공 장소 1~2장, 글 전체 4장 이상 "
          "(2026-10-27 사용자: 로마편 사진이 없다). Korea Travel 은 한국관광콘텐츠랩 고품질사진(공공누리 제1유형), "
          "World Travel 은 위키미디어 공용의 그 장소 카테고리를 먼저 찾는다.")


def forward(apps, schema_editor):
    SiteCategory = apps.get_model("blog_types", "SiteCategory")
    live = SiteCategory.objects.filter(deleted_at__isnull=True, parent=None, blog__platform="wordpress")
    for name, (old, new) in (("산과 캠핑", MOUNTAIN), ("Korea Travel", TRAVEL), ("World Travel", TRAVEL)):
        for cat in live.filter(name=name):
            if old in cat.concept and new not in cat.concept:
                cat.concept = cat.concept.replace(old, new, 1)
                cat.save(update_fields=["concept"])


class Migration(migrations.Migration):
    dependencies = [("blog_types", "0040_nunip_life")]
    operations = [migrations.RunPython(forward, migrations.RunPython.noop)]
