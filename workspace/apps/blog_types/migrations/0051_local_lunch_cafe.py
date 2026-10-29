"""black_lukey › 지역 놀거리: 점심·카페를 더 중요하게 (2026-10-29 사용자: 중간중간 점심·카페 추천이 사라졌나 —
'의무 아님 · 정말 유명한 곳만 · 맨 끝'이라 용문사 글부터 7편 연속 빠졌다. 선택은 그대로, 합쳐 최대 3곳, 괜찮으면 넣는다).

카테고리 컨셉의 순서 줄 · 맛집 줄을 바꾼다 (0008 이 넣은 말이 있을 때. 없으면 끝에 붙인다). 지우는 데이터 없음.
"""
from django.db import migrations

OLD_ORDER = "→ 갈 곳마다 소제목 → 맛집·카페(선택) → 마무리."
NEW_ORDER = "→ 갈 곳마다 소제목 (점심·카페는 동선 순서대로 그 사이에) → 마무리."
OLD_FOOD = ("- 맛집·카페 (의무 아님): 동선 위의 정말 유명한 곳만 1~3곳 (후기·지도로 확인). 짧은 설명 1~2문장 + `::: 맛집 | 이름` "
            "(🍽️ 대표 메뉴·가격 · ⏰ 영업·휴무 · 📍 주소) + 사진이 있으면 1장. 가 본 척하지 않는다.")
NEW_FOOD = "- 점심·카페 (2026-10-29 사용자: 선택이지만 중요하게): 동선 중간 점심 때·쉬어 갈 때에 맞춰, 동선 위·근처에서 후기·지도로 확인한 괜찮은 곳을 점심·카페 합쳐 최대 3곳. 괜찮은 곳이 있으면 넣는다 — 빼는 건 확인되는 곳이 정말 없을 때만. 하루 시간표에도 그 자리(예: `12:30 점심 · 가게 이름`)를 적고, 갈 곳 소제목 사이 동선 순서대로 짧은 설명 1~2문장 + `::: 맛집 | 이름` (🍽️ 대표 메뉴·가격 · ⏰ 영업·휴무 · 📍 주소) + 사진이 있으면 1장. 가 본 척하지 않는다."


def forward(apps, schema_editor):
    SiteCategory = apps.get_model("blog_types", "SiteCategory")
    for cat in SiteCategory.objects.filter(blog__name="black_lukey", name="지역 놀거리", deleted_at__isnull=True):
        text = cat.concept
        if "선택이지만 중요하게" in text:
            continue
        text = text.replace(OLD_ORDER, NEW_ORDER)
        text = text.replace(OLD_FOOD, NEW_FOOD) if OLD_FOOD in text else text.rstrip() + "\n" + NEW_FOOD
        cat.concept = text
        cat.save(update_fields=["concept"])


class Migration(migrations.Migration):
    dependencies = [("blog_types", "0050_travel_photos_max")]
    operations = [migrations.RunPython(forward, migrations.RunPython.noop)]
