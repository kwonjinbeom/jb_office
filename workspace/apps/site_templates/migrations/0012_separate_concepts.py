"""사이트·카테고리 컨셉이 서로 섞이지 않게 정리 (2026-10-27 사용자: 각 사이트 및 카테고리에 컨셉이 섞이지 않도록 확실하게).

- 다른 사이트·카테고리를 끌어다 쓰던 말을 뺀다: 축제·행사 '지역 놀거리와 같은 모양', World Travel '밤밤 해외여행처럼',
  눈잎 › 일상 '눈잎 › 일본 여행과 같다', Korea Travel · World Travel 사진 줄의 상대 카테고리 몫.
- 사이트 템플릿이 카테고리 글 모양과 부딪치던 곳: memorily 의 연재 말투(개발자 1인칭)가 애니 · AI 소식에도 들어가던 것을
  '블로그 자동화 연재 글만' 으로, 워드프레스 '인용 → 표 하나 → 본문' 을 카테고리 글 모양으로, black_lukey 인용 '1~3문장' 을 규칙의 '2~3개' 로,
  밤밤 '1인칭은 끝의' 를 '시황 노트 끝의' 로, 유디 모양의 '번호 단 짧은 물음' 이 일차 소제목 · 사용자가 쓴 일상 글과 부딪치던 것.
- 밤밤 › 해외여행은 위치 지도 줄만 있어 변환이 그 카테고리 글 모양을 몰랐다 → 작가 파일(writing_site_밤밤.md '해외여행')의 줄을 넣는다.
사용자는 이 값들을 화면에서 고친 적이 없다 (모두 migration). 그래도 고칠 줄이 그대로 있을 때만 바꾼다. 지우는 데이터 없음.
"""
from django.db import migrations

TEMPLATES = {  # 사이트 이름: [(칸, 옛 글, 새 글)]
    "memorily": [
        ("tone", "개발자 1인칭. AI를 쓰며 겪은 것·느낀 점을 내 방식으로, 과장 없이 담백하게.",
         "카테고리 컨셉의 말투를 따른다 (애니 · AI 소식은 각자 정해져 있다).\n"
         "블로그 자동화 연재 글만: 개발자 1인칭. AI를 쓰며 겪은 것·느낀 점을 내 방식으로, 과장 없이 담백하게."),
        ("structure", "겪은 상황 → 해 본 것(코드·화면) → 결과와 느낀 점 → 다음에 해 볼 것",
         "카테고리 컨셉의 글 모양을 따른다.\n"
         "블로그 자동화 연재 글만: 겪은 상황 → 해 본 것(코드·화면) → 결과와 느낀 점 → 다음에 해 볼 것"),
        ("rules", "직접 해 본 것만 쓴다. 코드·에러 메시지는 실제 것.",
         "블로그 자동화 연재 글만: 직접 해 본 것만 쓴다. 코드·에러 메시지는 실제 것.\n"
         "AI 소식은 써 본 척하지 않는다 — 다른 사람의 후기는 '써 본 사람들은 …'으로 쓰고 출처를 단다."),
    ],
    "black_lukey": [
        ("structure", "공통: 맨 위 인용 상자(결론 1~3문장) →", "공통: 맨 위 인용 상자(결론, 짧은 문장 2~3개) →"),
    ],
    "밤밤": [
        ("tone", "1인칭은 끝의 '내가 보는 다음 장'에서만.", "1인칭은 시황 노트 끝의 '내가 보는 다음 장'에서만."),
    ],
    "워드프레스": [
        ("tone", "영어 카테고리(국내여행·해외여행)", "영어 카테고리(Korea Travel·World Travel)"),
        ("structure", "카테고리 컨셉의 '글 모양'을 따른다. 공통: 맨 위 인용(2~3문장) → 표 하나 → 본문(정보 카드) → 마무리 서술.",
         "카테고리 컨셉의 '글 모양'을 따른다 (카테고리마다 순서·카드가 다르다). 맨 위 인용(리드)은 2~3문장."),
    ],
}

YUDI_HEAD = "연두 형광펜 밑칠 (번호 단 짧은 물음), 큰 단락"
TRAVEL_PHOTO = ("(2026-10-27 사용자: 로마편 사진이 없다). Korea Travel 은 한국관광콘텐츠랩 고품질사진(공공누리 제1유형), "
                "World Travel 은 위키미디어 공용의 그 장소 카테고리를 먼저 찾는다.")
ABROAD = (
    "해외 나라·도시 한 곳을 숫자로 소개한다 (계산형). 일본은 눈잎 › 일본 여행이 쓴다 — 여기는 일본 밖만. 같은 나라·도시는 14일 안에 다시 쓰지 않는다.\n"
    "- 'TOP 10'·'가볼만한곳 BEST' 나열 대신: 일정별 경비표 · 교통 패스 손익 · 공항에서 시내 비교 · 그 시기에만 되는 것(날짜) · 확인일이 붙은 입국 조건·환율.\n"
    "- 경험·감상 없이 담백하게. 갈 곳 정보는 정보 카드로 짧게 (📍 는 구글 지도 링크 `https://www.google.com/maps/search/?api=1&query=<이름>`).\n"
)
CATEGORIES = {  # (사이트, 카테고리): [(옛 글, 새 글)]
    ("눈잎", "일본 여행"): [(YUDI_HEAD, "연두 형광펜 밑칠 (소제목 말은 위 짜임새대로 — 일차는 `## N일차 · 그날 지역`), 큰 단락")],
    ("눈잎", "일상"): [("화면 모양 (유디 블로그의 화면 짜임 — 눈잎 › 일본 여행과 같다, 붙여 넣는 HTML 이 그린다",
                       "화면 모양 (유디 블로그의 화면 짜임, 붙여 넣는 HTML 이 그린다"),
                      (YUDI_HEAD, "연두 형광펜 밑칠 (소제목 말은 사용자가 쓴 원문 그대로), 큰 단락")],
    ("black_lukey", "축제·행사"): [("(2026-10-23 사용자 — 지역 놀거리와 같은 모양)", "(2026-10-23 사용자)")],
    ("워드프레스", "World Travel"): [("(2026-10-26 사용자: 밤밤 해외여행처럼)", "(2026-10-26 사용자)"),
                                 (TRAVEL_PHOTO, "(2026-10-27 사용자: 로마편 사진이 없다). 위키미디어 공용의 그 장소 카테고리를 먼저 찾는다.")],
    ("워드프레스", "Korea Travel"): [(TRAVEL_PHOTO, "(2026-10-27 사용자). 한국관광콘텐츠랩 고품질사진(공공누리 제1유형)을 먼저 찾는다.")],
}


def forward(apps, schema_editor):
    SiteTemplate = apps.get_model("site_templates", "SiteTemplate")
    SiteCategory = apps.get_model("blog_types", "SiteCategory")
    for site, changes in TEMPLATES.items():
        for tpl in SiteTemplate.objects.filter(blog__name=site):
            fields = []
            for field, old, new in changes:
                value = getattr(tpl, field)
                if old in value and new not in value:
                    setattr(tpl, field, value.replace(old, new, 1))
                    fields.append(field)
            if fields:
                tpl.save(update_fields=fields)
    live = SiteCategory.objects.filter(deleted_at__isnull=True)
    for (site, name), changes in CATEGORIES.items():
        for cat in live.filter(blog__name=site, name=name):
            concept = cat.concept
            for old, new in changes:
                if old in concept:
                    concept = concept.replace(old, new, 1)
            if concept != cat.concept:
                cat.concept = concept
                cat.save(update_fields=["concept"])
    for cat in live.filter(blog__name="밤밤", name="해외여행"):
        if "계산형" not in cat.concept:
            cat.concept = ABROAD + cat.concept
            cat.save(update_fields=["concept"])


class Migration(migrations.Migration):
    dependencies = [("site_templates", "0011_wordpress_format_css"), ("blog_types", "0041_photo_counts")]
    operations = [migrations.RunPython(forward, migrations.RunPython.noop)]
