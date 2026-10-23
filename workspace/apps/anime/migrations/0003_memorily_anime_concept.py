"""memorily › 애니 카테고리 컨셉에 회차정리 글 형식을 적는다 (2026-10-23 사용자: 지금까지 애니 글에서 요구하고 해 온 형식을
사이트별 템플릿에 정리해 두라). 변환 요청문과 애니 총정리의 '글쓰기·변환' 안내문이 이 컨셉을 그대로 넣는다.

컨셉이 비었으면 채우고, 이미 다른 말이 있으면 그 뒤에 붙인다. 이미 넣었으면(첫 줄이 있으면) 건드리지 않는다. 지우는 데이터 없음.
"""
from django.db import migrations

MARK = "애니 회차정리 글 — 작품 하나에 글 하나"
CONCEPT = MARK + """, 제목은 `<작품> 회차정리 애니만화 환산기 명장면 등 모음`. 자세한 순서는 저장소 `애니총정리/00_작업순서.md`.

글 모양
- 맨 위 요약 없이 바로 '화수 환산기'로 시작한다. 해요체로 짧게, 글보다 표.
- 순서: 화수 환산기(`[환산기: <작품키>]` 한 줄 → 대표 그림) → 그 작품에서 가장 헷갈리는 것(두 판 차이 · 몇 기 몇 화 · 이어 보기 · 지금 어디까지) → 막대 그림 → 장별 대응 → 애니 다음 만화 → 애니 오리지널 회차 → 자주 묻는 것 → 극장판 → 명장면 몇 화 → 그 밖의 장면 표 → 출처 · 사진 저작권. 검색어를 보고 빼고 더한다.
- 이름 · 줄임말은 한국에서 부르는 그대로 (나히아, 강연금, 헌터헌터). 일본 팬 말 · 어려운 말은 쓰지 않는다 ('통산 회차' 대신 '이어 센 화').
- 몇 기로 찾는 작품은 기 표(기 · 회차 · 이어 세면 · 만화 화와 권 · 방영). 어느 기준(일본 DVD · 라프텔 등)인지 밝힌다.
- 두 판이 있으면(헌터×헌터 1999 · 2011, 강철의 연금술사 2003 · 브라더후드) 왜 나뉘었는지 짧게 쓰고 비교표.
- 극장판이 있으면 명장면 앞에 표(개봉 · 보는 위치). 보는 위치는 공식이 아니라 흔히 안내되는 자리라고 밝히고, 엇갈리면 그렇게 적는다.
- 명장면: `**장면** · 애니 몇 화 · 만화 몇 화` 한 줄 다음에 사진. 사진은 5장, 나머지 장면은 표로.
- 끝: `출처: <작품> 위키(fandom) 회차별 원작 화수, Anime Filler List. <날짜> 확인` 과 `사진: ⓒ 원작자 / 출판사 · 방송사 · 제작사`.

사진
- 표지는 쓰지 않는다. 장면 사진은 작품 fandom 위키의 회차 화면, 폭 620 (`/revision/latest/scale-to-width-down/620`).
- 가공이미지 2장: 대표(620×325, 작품 색 하나)와 '어디까지 만화 내용일까' 막대 — `애니환산기/그림.py` 로 그린다.
- 글쓰기 때 사진을 못 채웠으면 자리만 두고 변환 때 채운다. 애니 총정리의 '글쓰기·변환' 버튼은 둘을 한 번에 한다.

환산기
- 데이터는 `애니환산기/data/<작품키>.json` (회차마다 [만화 첫 화, 끝 화, 종류 1 원작 · 2 원작+애니 · 0 오리지널]), `build.py` 로 스킨 파일을 다시 만든다.
- 새 작품 환산기는 티스토리 스킨에 `스킨에_붙일것.html` 을 다시 붙여야 뜬다."""


def forward(apps, schema_editor):
    Blog = apps.get_model("blog_rules", "Blog")
    SiteCategory = apps.get_model("blog_types", "SiteCategory")
    blog = Blog.objects.filter(name="memorily", deleted_at__isnull=True).first()
    cat = blog and SiteCategory.objects.filter(blog=blog, name__startswith="애니", deleted_at__isnull=True).order_by("pk").first()
    if not cat or MARK in cat.concept:
        return
    cat.concept = f"{cat.concept.rstrip()}\n\n{CONCEPT}" if cat.concept.strip() else CONCEPT
    cat.save(update_fields=["concept"])


class Migration(migrations.Migration):

    dependencies = [
        ("anime", "0002_seed_titles"),
        ("blog_types", "0020_site_links"),
        ("blog_rules", "0009_site_targets"),
    ]

    operations = [migrations.RunPython(forward, migrations.RunPython.noop)]
