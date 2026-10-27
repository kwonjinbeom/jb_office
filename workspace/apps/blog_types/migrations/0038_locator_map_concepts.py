"""위치 지도를 카테고리 컨셉에 자세히 (2026-10-27 사용자: "이거 각 카테고리 컨셉에 잘 기록해줘") + 국내 지역 놀거리에도.

1. 밤밤 › 해외여행 · 워드프레스 › World Travel: 0037 의 짧은 한 줄을 사이트별 지도 모양까지 적은 줄로 바꾼다.
2. black_lukey › 지역 놀거리: 순서의 '공감 한 줄' 자리를 '위치 지도 → 여는 말'로, 두 줄을 더한다
   (사용자: 우리나라 지도와 지역 표시, '오늘은~ · 뭐가 유명한~'으로 지역을 여는 말, 그 소재를 고른 까닭 — 제철·단풍·벚꽃·많이 찾는).
사용자가 이미 고친 줄은 건드리지 않는다. 지우는 데이터 없음.
"""
from django.db import migrations

OLD = ("- 위치 지도: 맨 위 인용 바로 다음(대표 사진이 있으면 그 다음)에 그 도시 위치 지도 1장 — 가공이미지, 변환이 그린다 "
       "(2026-10-27 사용자: 어디인지 감이 안 온다).")
BAMBAM = ("- 위치 지도 (2026-10-27 사용자: 어디인지 감이 안 온다): 맨 위 인용 바로 다음(인용 아래 대표 사진이 있으면 그 다음)에 1장, "
          "변환이 그린다 (변환그림/위치지도.py 밤밤). 모양: 제목 '<나라> <도시>' + '<대륙> · 서울에서 직선 약 N km' 한 줄, "
          "두 칸 — 왼쪽 서울에서 그 도시까지 점선, 오른쪽 그 나라를 빨강으로 칠하고 독자가 아는 이웃 도시 3~5곳. "
          "흰 바탕·회색 땅·빨강 한 가지, 출처 'Natural Earth'. 캡션 줄 없음, 대표 사진으로 쓰지 않는다.")
WORLD = ("- 위치 지도 (Location map, 2026-10-27 사용자: 어디인지 감이 안 온다): 리드 바로 다음(대표 사진이 있으면 그 다음)에 1장, "
         "변환이 그린다 (변환그림/위치지도.py 워드프레스). 모양: 세리프 제목 '<City>, <Country>' + "
         "'<Subregion> · N km from London · New York · Sydney' 한 줄, 넓은 지도 한 장에 그 나라를 테라코타로 칠하고 "
         "이웃 나라 이름·이웃 도시 3~5곳(영어), 오른쪽 아래 작은 세계 지도에 지금 보는 범위 네모. 글모양.css 여행 색. "
         "대체 텍스트 'Map: where <City> is', 캡션 없음, 대표 이미지로 쓰지 않는다.")
LOCAL_ORDER = ("→ 공감 한 줄 → 하루 시간표", "→ 위치 지도 → 여는 말 → 하루 시간표")
LOCAL = "\n".join([
    "- 위치 지도 (2026-10-27 사용자): 맨 위 인용 상자 바로 다음에 1장, 변환이 그린다 (변환그림/위치지도.py black_lukey <시도 코드>). "
    "모양: 제목 '<시도 줄임> <도시>'(경남 통영) + '<시도> · 서울에서 직선 약 N km' 한 줄, 두 칸 — 왼쪽 우리나라 전체에 그 시도를 "
    "연한 초록으로 칠하고 서울 점, 오른쪽 그 도시 가까이(시도 경계 · 이웃 도시 3~5곳). 정보 카드 '가 볼 곳'과 같은 초록. "
    "캡션 없음, 대표 사진으로 쓰지 않는다.",
    "- 여는 말 (2026-10-27 사용자): 지도 바로 아래 3~4줄로 지역을 연다. ① '오늘은 경남 통영이에요.' ② 어디쯤인지 한 줄"
    "(이웃 도시·바다·산 기준) ③ 왜 지금인지 — 그 소재를 고른 까닭 그대로 (제철 먹거리 · 단풍·벚꽃·억새 · 축제 날짜 · "
    "요즘 많이 찾는 까닭) ④ 공감 한 줄. 확인한 사실만, '유명한'은 근거가 있을 때만.",
])


def forward(apps, schema_editor):
    SiteCategory = apps.get_model("blog_types", "SiteCategory")
    live = SiteCategory.objects.filter(deleted_at__isnull=True, parent=None)
    for qs, line in ((live.filter(blog__name="밤밤", name="해외여행"), BAMBAM),
                     (live.filter(blog__platform="wordpress", name="World Travel"), WORLD)):
        for cat in qs:
            if OLD in cat.concept:
                cat.concept = cat.concept.replace(OLD, line)
            elif "위치 지도 (" not in cat.concept:
                cat.concept = (cat.concept.rstrip() + "\n" + line).strip()
            else:
                continue
            cat.save(update_fields=["concept"])
    for cat in live.filter(blog__platform="naver", name="지역 놀거리"):
        if "위치 지도" in cat.concept:
            continue
        concept = cat.concept.replace(*LOCAL_ORDER, 1)
        lines = concept.split("\n")
        at = next((i + 1 for i, s in enumerate(lines) if s.startswith("- 순서:")), len(lines))
        cat.concept = "\n".join(lines[:at] + LOCAL.split("\n") + lines[at:]).strip()
        cat.save(update_fields=["concept"])


class Migration(migrations.Migration):
    dependencies = [("blog_types", "0037_travel_locator_map")]
    operations = [migrations.RunPython(forward, migrations.RunPython.noop)]
