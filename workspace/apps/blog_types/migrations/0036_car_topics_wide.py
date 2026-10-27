"""워드프레스 › 드라이브·자동차를 넓힌다 (2026-10-27 사용자: 차에 관한 건 신차가 아니라도 무궁무진한데 '소재 없음'이 나왔다).

1. 글 분류 소재 '드라이브·자동차'의 방향·독자의 질문: 신차·제도 소식만이 아니라 차 종류·구조, 차 한 대 깊게, 비교·고르기, 상식·통계까지.
2. 사이트 카테고리 컨셉: 글 종류 A~D 뒤에 E~H 를 더한다 (날짜 있는 소식이 먼저, 없으면 상시 소재). 사용자가 고친 컨셉이면 건드리지 않는다.
"""
from django.db import migrations

DIRECTION = "차 가진 사람이 흥미로워하는 것 전부 — 신차 · 돈과 제도 · 기능·관리 · 차 종류·구조 · 차 한 대 깊게 · 비교·고르기 · 상식·통계 · 드라이브 코스"
QUESTION = "이 차 뭐가 달라졌지, 내 차에 얼마 들지, 이건 무슨 뜻이지, 뭘 살까, 이번 주말 어디로 달리지"
OLD_DIRECTION = "차 가진 사람들이 궁금해하는 것 전부 — 신차·연식 변경 · 기름값·통행료·자동차세·보험·검사 같은 돈과 제도 · 자동차 기능·상식 · 드라이브 코스"

ANCHOR = "- 숫자는 제조사 가격표·뉴스룸"
MORE = "\n".join([
    "날짜 있는 소식(A·B, 시즌 C)이 먼저, 없으면 아래 상시 소재로 — 매일 쓸 거리가 있다 (2026-10-27 사용자).",
    "E. 차 종류·구조 해설 (차급 · 차체 형태 · 파워트레인 · 구동방식 · 변속기 · 타이어 규격 읽기) — `::: 요약 | 한눈에` → 기준 대조표(법·업계·통행료처럼 기준이 여럿이면 나란히) → "
    "대표 차종을 표에 꽂은 예시 → 내 돈에 닿는 곳(세금·보험·혜택) → 헷갈리는 말 정리.",
    "F. 차 한 대 깊게 (신차가 아닌 스테디셀러·단종차·명차·브랜드 이야기) — `::: 차 | 차명` → 세대별 표(연도 | 바뀐 점 | 시작가) → 왜 오래 팔리나(숫자로) → 중고로 볼 때 볼 것.",
    "G. 비교·고르기 (같은 예산 다른 차 · 하이브리드 vs 가솔린 손익분기 · 신차 vs 중고 · 할부·리스·렌트) — 고르는 기준 2~4개 → 비교표 → 직접 계산(연 주행거리별) → 사람 유형별 선택.",
    "H. 상식·통계 (월별 판매 순위 · 리콜 · 번호판·차명의 뜻 · 운전 규칙 · 모터쇼) — 숫자 표 하나가 주인공, 기준일·출처 필수. 월별 판매 실적은 매월 1~2일, 리콜은 국토부 발표 날이 쓸 때.",
])


def forward(apps, schema_editor):
    Category = apps.get_model("blog_types", "Category")
    SiteCategory = apps.get_model("blog_types", "SiteCategory")
    for cat in Category.objects.filter(section__name="워드프레스", name="드라이브·자동차", deleted_at__isnull=True):
        if cat.direction.strip() in ("", OLD_DIRECTION):
            cat.direction, cat.question = DIRECTION, QUESTION
            cat.save(update_fields=["direction", "question"])
    for cat in SiteCategory.objects.filter(blog__platform="wordpress", parent=None, name="드라이브·자동차", deleted_at__isnull=True):
        if "E. 차 종류" not in cat.concept and ANCHOR in cat.concept:
            cat.concept = cat.concept.replace(ANCHOR, MORE + "\n" + ANCHOR, 1)
            cat.save(update_fields=["concept"])


class Migration(migrations.Migration):
    dependencies = [("blog_types", "0035_placement_wp_draft")]
    operations = [migrations.RunPython(forward, migrations.RunPython.noop)]
