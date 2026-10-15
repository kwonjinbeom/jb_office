"""두 번째 대분류 '광고 수익 (조회수)': 판매를 빼고 조회수로 광고 수익을 내는 분야 8개.

처음 값: 콘텐츠/블로그_카페/포스팅자동화/09_조회수형_대분류.md 2절 표 (2026-10-15 사용자: "전부 다 괜찮다, 정리해줘").
타입은 '정형 타입 예시'를 글 모양별로 묶고, 표의 예시는 예시 제목으로 넣었다. 하위는 사용자가 화면에서 채운다.
같은 이름의 대분류가 이미 있으면 아무것도 하지 않는다.
"""
from django.db import migrations

A, C = "A. 시즌 달력형", "C. 질문형 해설"
NOTE = ("판매를 빼고 조회수로 광고 수익을 내는 분야. 날짜·숫자는 매번 바뀌고 글 모양은 같아서 찍어내기에 맞다. "
        "글마다 숫자 하나에 판단 하나를 붙인다.")

SEED = [
    ("금융·시장", "매일 새 질문이 생기고 광고 단가가 높은 분야", "오늘 왜 빠졌지, 다음 달엔 뭐가 있지",
     "재료: 한국거래소, DART 공시, 한국은행, 증권사 공모 일정\n손맛: \"오늘 숫자 중 하나만 본다면 이것\" 관점 한 줄, 어제와 비교\n"
     "주의: 사라·팔라 같은 투자 권유 금지, 수익 보장 표현 금지. 원인 설명과 일정만", [
         ("일일 시황 · 오늘 ○○ 왜", C, "오늘 코스피 하락 이유\n나스닥 상승 이유"),
         ("일정 달력", A, "다음 달 공모주 일정\n금리 결정일 정리"),
         ("기준선 해설", C, "환율 1,400원 넘으면"),
     ]),
    ("정책·내 돈", "\"나도 받나?\"는 가족 단위로 공유된다", "나도 받을 수 있나, 언제 신청하지",
     "재료: 정부24, 복지로, 청약홈, 국세청\n손맛: 출생연도·소득으로 내 줄 찾기 표 (T01 독감)\n"
     "주의: 공식 기관 자료만. 날짜가 바뀌면 새 글 말고 기존 글을 고친다", [
         ("대상·신청일 (내 줄 찾기)", C, "○○지원금 대상·신청일"),
         ("일정 달력", A, "청약 일정"),
         ("바뀐 점 정리", C, "연말정산 바뀐 점\n건강보험료·국민연금 바뀌는 것"),
     ]),
    ("생활 일정·요금", "시즌마다 같은 질문이 반복된다", "이번에 뭐가 바뀌지, 우리 집은 얼마나",
     "재료: 기상청, 한전, 도로공사, 지자체 공지\n손맛: \"우리 집은 얼마 오르나\" 계산 예시", [
         ("달력", A, "공휴일·연휴 달력\n명절 고속도로"),
         ("바뀌는 것 + 우리 집 계산", C, "전기·가스요금 바뀌는 달\n쓰레기 배출 바뀐 점"),
     ]),
    ("콘텐츠·엔터", "조회수 자체는 가장 크다 (광고 단가는 낮은 편)", "이번 주 뭐 보지, 그 결말은 무슨 뜻이지",
     "재료: 넷플릭스·티빙 공식 공개일, 방송사 편성표\n손맛: 감상·해석은 사람만 쓸 수 있다. 스포일러 단계 표시\n"
     "주의: 루머·사생활 금지, 공식 이미지 무단 사용 금지", [
         ("이번 주 공개작", A, "이번 주 OTT 신작\n시즌2 공개일"),
         ("결말·해석", "새 뼈대 필요 (줄거리 요약 없이 해석 중심)", "드라마 결말 해석"),
         ("티켓팅 일정", A, "콘서트 티켓팅 일정"),
     ]),
    ("스포츠 일정", "경기 당일에 몰린다", "오늘 경기 어디서 보지",
     "재료: 리그 공식 일정, 중계사 공지\n손맛: 몰라도 보는 법 (T10 롤드컵)", [
         ("오늘 경기 · 중계 어디서", C, "오늘 경기 중계 어디서\n손흥민·이강인 다음 경기"),
         ("대회 일정 + 입문", C, "롤드컵·KBO 일정"),
     ]),
    ("IT·앱", "업데이트 알림이 뜰 때마다 검색된다", "업데이트 해도 되나, 언제 나오지",
     "재료: 애플·삼성 공식 릴리스 노트\n손맛: \"지금 할까 미룰까\" 판단 한 줄", [
         ("업데이트, 해야 하나", C, "iOS 업데이트 바뀐 점, 해야 하나\n카톡 업데이트"),
         ("출시일·사전예약", A, "갤럭시 출시일·사전예약"),
     ]),
    ("시험·교육", "정해진 날짜에 수험생과 가족이 같이 찾는다", "언제 접수하지, 발표는 언제지",
     "재료: 평가원, Q-Net, 사이버국가고시센터\n손맛: 그 전에 해 둘 것 (T14 수능)", [
         ("시험 달력", A, "수능·자격증·공무원 시험 일정\n원서 접수"),
         ("발표일 · 그 전에 해 둘 것", C, "합격 발표일"),
     ]),
    ("여행·계절", "매년 같은 시기에 다시 찾는다", "언제 가면 제일 좋지",
     "재료: 산림청, 기상청, 지자체 축제 공지\n손맛: \"기준이 달라 날짜가 다르다\" 같은 해석 (T03 단풍)", [
         ("예측 해설", C, "벚꽃·단풍 예측"),
         ("축제·개장 달력", A, "지역 축제 달력\n해수욕장 개장일"),
     ]),
]


def forward(apps, schema_editor):
    Section = apps.get_model("blog_types", "Section")
    Category = apps.get_model("blog_types", "Category")
    PostType = apps.get_model("blog_types", "PostType")
    if Section.objects.filter(name="광고 수익 (조회수)").exists():
        return
    order = (Section.objects.order_by("-order").values_list("order", flat=True).first() or 0) + 1
    section = Section.objects.create(name="광고 수익 (조회수)", note=NOTE, order=order)
    for c_order, (name, direction, question, note, types) in enumerate(SEED, start=1):
        cat = Category.objects.create(section=section, code="ABCDEFGH"[c_order - 1], name=name, direction=direction,
                                      question=question, note=note, order=c_order)
        for t_order, (t_name, skeleton, examples) in enumerate(types, start=1):
            PostType.objects.create(category=cat, name=t_name, skeleton=skeleton, examples=examples, order=t_order)


class Migration(migrations.Migration):
    dependencies = [("blog_types", "0005_direction_label")]
    operations = [migrations.RunPython(forward, migrations.RunPython.noop)]
