"""워드프레스 › Korea Travel 에도 위치 지도 (2026-10-27 사용자: "워드프레스에서 국내여행에도 지도 같은 느낌으로 넣어줘").

World Travel 과 같은 짜임 — 그 도시 가까이 넓은 지도 + 구석에 우리나라 작은 지도. 순서에 '리드 → 위치 지도'를 넣고 한 줄 더한다.
이미 있으면 건드리지 않는다. 지우는 데이터 없음.
"""
from django.db import migrations

ORDER = ("순서: 리드 → `## {City} at a Glance`", "순서: 리드 → 위치 지도 → `## {City} at a Glance`")
LINE = ("- 위치 지도 (Location map, 2026-10-27 사용자: 국내여행에도 지도): 리드 바로 다음(대표 사진이 있으면 그 다음)에 1장, "
        "변환이 그린다 (변환그림/위치지도.py 워드프레스 <시도 코드>). 모양: 세리프 제목 '<City>, South Korea' + "
        "'<Province> · N km from Seoul · N km from Busan' 한 줄, 넓은 지도 한 장에 그 시도를 테라코타로 칠하고 "
        "이웃 도시 3~5곳·이웃 시도 이름(영어), 오른쪽 아래 우리나라 작은 지도에 지금 보는 범위 네모. 글모양.css 여행 색. "
        "대체 텍스트 'Map: where <City> is', 캡션 없음, 대표 이미지로 쓰지 않는다.")


def forward(apps, schema_editor):
    SiteCategory = apps.get_model("blog_types", "SiteCategory")
    for cat in SiteCategory.objects.filter(deleted_at__isnull=True, parent=None, blog__platform="wordpress", name="Korea Travel"):
        if "위치 지도" in cat.concept:
            continue
        cat.concept = (cat.concept.replace(*ORDER, 1).rstrip() + "\n" + LINE).strip()
        cat.save(update_fields=["concept"])


class Migration(migrations.Migration):
    dependencies = [("blog_types", "0038_locator_map_concepts")]
    operations = [migrations.RunPython(forward, migrations.RunPython.noop)]
