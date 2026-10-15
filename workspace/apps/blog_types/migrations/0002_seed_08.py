"""처음 값: 콘텐츠/블로그_카페/포스팅자동화/08_수익형_카테고리.md 1절 표 (2026-10-15 사용자 확정).

하위는 문서에 근거가 있는 것만 넣었다: B › A vs B 는 05 생성규칙 3절 C 의 변형, C › 시즌 달력은 06 시즌 달력.
나머지 하위는 사용자가 화면에서 채운다. 이미 카테고리가 하나라도 있으면 아무것도 넣지 않는다.
"""
from django.db import migrations

SEED = [
    ("A", "문제 해결", "불편 → 해결템", "이거 왜 이러지, 뭐가 필요하지", "all", [
        ("원인 해설 + 해결 도구", "C. 질문형 해설", "겨울마다 정전기 심하면 가습기보다 먼저 볼 것", []),
        ("상황별 준비물", "C. 질문형 해설 (준비물 표)", "첫 캠핑, 텐트 말고 먼저 사야 할 6개", []),
    ]),
    ("B", "고르기", "살 건 정했는데 뭘 살지 모름", "둘 중 뭐가 나한테 맞지", "all", [
        ("A vs B", "B. 비교·고르기형", "에어프라이어 바스켓형 vs 오븐형, 1인 가구라면", [
            ("두 개만 비교", "가장 많이 고민하는 두 개만 놓고 결론을 낸다."),
            ("입문용 vs 오래 쓸 것", "처음 사는 사람과 오래 쓸 사람으로 나눠 결론을 둘로 낸다."),
            ("이미 가진 걸로 충분한 경우", "안 사도 되는 사람을 먼저 걸러 주는 비교. 신뢰가 생긴다."),
        ]),
        ("○○한 사람용 추천", "B. 비교·고르기형", "자취방 좁은 사람용 건조대", []),
        ("기준 정리", "B. 비교·고르기형", "전기요 고를 때 W수보다 먼저 볼 숫자", []),
    ]),
    ("C", "타이밍", "언제 사야 싸나", "지금 사도 되나, 언제가 싸지", "all", [
        ("시즌 달력", "A. 시즌 달력형", "11월 세일 달력, 품목별 언제 살까", [
            ("세일 행사", "K-세일페스타·블랙프라이데이·광군제처럼 날짜가 정해진 행사를 한 장에."),
            ("계절 품목", "난방·가습·김장처럼 철이 오기 전에 사야 하는 품목."),
            ("기념일·시험", "빼빼로데이·수능처럼 날짜에 맞춰 사는 물건."),
        ]),
        ("가격 추적 / 행사 정리", "A. 시즌 달력형", "다이슨 블프 때 평소보다 얼마나 싸졌나", []),
    ]),
    ("D", "선물", "누구에게 줄까", "누구에게 뭘 주지", "all", [
        ("받는 사람·예산별", "B. 비교·고르기형 (기준 = 받는 사람·예산)", "수능 끝난 조카에게 3만 원 안쪽", []),
        ("시즌 선물", "B. 비교·고르기형 (기준 = 받는 사람·예산)", "빼빼로데이 말고 11/11에 줄 만한 것", []),
    ]),
    ("E", "비용 계산", "돈 아끼기", "사는 게 이득이긴 한가", "all", [
        ("사는 게 나은지 비교", "B. 비교·고르기형 (금액·기간 비교표)", "김장, 직접·절임배추·사 먹기", []),
        ("유지비·소모품 계산", "B. 비교·고르기형 (금액·기간 비교표)", "정수기 렌탈 vs 구매, 3년 쓰면", []),
    ]),
    ("F", "생활 장면", "따라 하기", "저 사람처럼 하려면 뭐가 있어야 하지", "all", [
        ("루틴·세팅", "새 뼈대 필요 (장면 → 쓰는 도구 → 대체품)", "퇴근 후 10분 홈트, 쓰는 도구 전부", []),
        ("공간 꾸미기", "새 뼈대 필요 (장면 → 쓰는 도구 → 대체품)", "원룸 겨울 단열, 3만 원으로 끝내기", []),
    ]),
    ("G", "여행·체험", "쇼핑커넥트 전용 · 예약을 판다", "어디로, 무엇을 예약하지", "naver", [
        ("코스 + 예약 연결", "새 뼈대 필요 (코스 → 예약 상품 비교)", "11월 단풍 끝물, 남쪽 1박 패키지 고르기", []),
    ]),
]


def seed(apps, schema_editor):
    Category = apps.get_model("blog_types", "Category")
    PostType = apps.get_model("blog_types", "PostType")
    SubType = apps.get_model("blog_types", "SubType")
    if Category.objects.exists():
        return
    for c_order, (code, name, direction, question, platform, types) in enumerate(SEED, start=1):
        cat = Category.objects.create(code=code, name=name, direction=direction, question=question,
                                      platform=platform, order=c_order)
        for t_order, (t_name, skeleton, example, subs) in enumerate(types, start=1):
            pt = PostType.objects.create(category=cat, name=t_name, skeleton=skeleton, examples=example, order=t_order)
            for s_order, (s_name, s_note) in enumerate(subs, start=1):
                SubType.objects.create(post_type=pt, name=s_name, note=s_note, order=s_order)


class Migration(migrations.Migration):
    dependencies = [("blog_types", "0001_initial")]
    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
