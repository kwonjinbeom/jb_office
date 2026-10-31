"""black_lukey › 세일 이벤트를 검색량 순으로 고친다 (2026-10-31 사용자: "고정은 무조건 우선순위, 그 외도 보는 건 좋다.
검색량이 낮은 건 쓰고 싶지 않다. 글감이 여러 개면 나오는 만큼 다 쓰고, 없으면 B안, 전부 없으면 못 쓴다").

구글 트렌드 12개월(올영세일 = 100)로 재 보니 29CM·쿠팡·코리아세일페스타·11번가는 0.2~6% → 고정은 올리브영·유니클로·무신사·자라·SSG.
1. 글 분류 black_lukey › 세일 이벤트의 방향·독자의 질문.
2. 사이트 카테고리 black_lukey › 세일 이벤트 컨셉 — 0053 이 넣은 글 그대로일 때만 바꾼다 (사용자가 고쳤으면 두고 알린다).
같은 글이 작가 파일(일일루틴/프롬프트/writing_site_black_lukey.md)·출처표(writing_sources.md)에도 있다 — 고칠 때 모두. 지우는 데이터 없음.
"""
from django.db import migrations

NAME = "세일 이벤트"
OLD_HEAD = "세일 이벤트: 올리브영(올영세일·올영데이) · 무신사(블랙프라이데이·무진장) · 유니클로(감사제) · 29CM · 쿠팡"
DIRECTION = "검색량 순: 고정 5곳(올리브영·유니클로·무신사·자라·SSG) 세일 회차 → 혜택 시즌(블프·기념일·수험생 할인) → 둘 다 없으면 생활 혜택 (공식 공지만)"
QUESTION = "이번 세일·혜택 언제 하고 뭘 챙기면 좋지"
CONCEPT = """세일 이벤트: 검색량 순이 우선순위 (2026-10-31 구글 트렌드 12개월, 올영세일 = 100). 공식 공지가 없으면 쓰지 않는다.
- 고정 5곳 (무조건 먼저, 이 순서): 올리브영(올영세일·올영데이) 100 · 유니클로(감사제) 53 · 무신사(무진장·블프) 48 · 자라(블프·시즌오프) 31 · SSG(쓱데이·신세계 세일) 28. 공식 공지한 한 회차를 한 편에 (시작 7~10일 전 ~ 진행 첫 주).
- A 혜택 시즌 (세일이 아니어도 많이 찾는 날): 블프 총정리 282 · 화이트데이 211 · 발렌타인데이 192 · 크리스마스 선물·케이크 사전예약 86·40 · 수험생 할인 55 · 빼빼로데이 46 · 어버이날 선물 33. 고정과 A 는 '있음'이면 나오는 만큼 다 쓴다.
- B 생활 혜택 (고정·A 가 하나도 없는 날만 1편): 다이소 뷰티 신상 38 · 네이버페이 적립 36 · 배달·피자 할인 31 · 스타벅스 프리퀀시 23.
- 쓰지 않는 것: 검색량이 낮은 곳(29CM·쿠팡·코리아세일페스타·11번가 등 — 그 외 브랜드는 자라보다 많이 찾을 때만) · 품목 하나의 구매 타이밍·가격 추이(노트북·패딩 언제 살까) · IT 기기 할인(memorily › IT 할인) · 새 제품(신제품 출시) · 팝업스토어(축제·행사).
글 모양 셋 (black_lukey › 출시의 짜임을 세일에 맞게):
- 한 회차 소식 (고정): 맨 위 인용(결론 2~3문장: 언제부터 언제까지 · 가장 큰 혜택 한 줄) → 한눈에 표(행사 · 기간 · 할인 · 쿠폰·적립 · 대상) → 지난 회차 표(회차 · 기간 · 최대 할인, 확인된 것만) → 혜택마다 소제목 → 이번에 살 만한 것 → 놓치기 쉬운 것 → 공식 공지 보는 곳
- 시즌 혜택 모음 (A): 맨 위 인용(그날까지 남은 날 · 가장 큰 혜택) → 한눈에 표(브랜드 · 기간 · 혜택 · 조건, 많이 찾는 브랜드부터) → 브랜드마다 소제목 + 카드 → 놓치기 쉬운 것 → 공식 공지 보는 곳. 공식 공지로 확인한 브랜드만 3~6곳.
- 이번 달 혜택 정리 (B): 맨 위 인용 → 한눈에 표(혜택 · 기간 · 조건) → 혜택마다 소제목 + 카드 → 놓치기 쉬운 것 → 공식 공지 보는 곳.
- 행사 카드 `::: 제품 | 행사 이름` (카드 종류는 장소·맛집·작품·제품뿐 — IT 할인과 같이 제품): 📅 기간 · ⏰ 시작 시각 · 💸 할인 · 🎟️ 쿠폰·적립 · 👤 대상(회원 등급·앱 전용) · 🔗 공식 공지.
- 이번에 살 만한 것: 그 브랜드 공식 기획전에 오른 것 중 3~5개, 상품마다 사진 1장 · 2~3문장(왜 이번이 싼지 · 누구에게). 써 본 척하지 않는다.
- 놓치기 쉬운 것: 쿠폰 받는 시각 · 등급별 쿠폰 · 앱 전용 · 같이 안 되는 혜택을 짧은 목록으로.
- 기간·할인율·쿠폰은 브랜드 공식 앱 공지·이벤트 페이지로 확인한 것만. 표 아래에 '○월 ○일 공식 공지 기준 · 바뀔 수 있어요' 한 줄.
- 사진: 공식 기획전 배너 · 매장 · 상품 실물 (직접 찍은 것 우선). 링크는 조회용 공식 페이지 — 쇼핑커넥트는 참여 스마트스토어 상품만, 대가 문구는 첫 부분."""


def forward(apps, schema_editor):
    Category = apps.get_model("blog_types", "Category")
    SiteCategory = apps.get_model("blog_types", "SiteCategory")
    Category.objects.filter(section__name="black_lukey", name=NAME, deleted_at__isnull=True).update(
        direction=DIRECTION, question=QUESTION)
    for sc in SiteCategory.objects.filter(blog__name="black_lukey", parent=None, name=NAME, deleted_at__isnull=True):
        if not sc.concept.strip() or sc.concept.startswith(OLD_HEAD):
            sc.concept = CONCEPT
            sc.save(update_fields=["concept"])
        else:
            print(f"\n  blog_types 0055: black_lukey › {NAME} 컨셉을 사람이 고쳐서 그대로 둠")


class Migration(migrations.Migration):
    dependencies = [("blog_types", "0054_memorily_branches")]
    operations = [migrations.RunPython(forward, migrations.RunPython.noop)]
