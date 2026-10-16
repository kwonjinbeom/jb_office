"""처음 값: 2026-10-16 사용자와 정한 운영 계획 (근거: 포스팅자동화 10·11 문서).

블로그나 규칙이 이미 있으면 넣지 않는다 (화면에서 고친 값을 덮지 않게).
"""
from django.db import migrations

BLOGS = [
    dict(name="memorily", platform="tistory", status="active", address="", account="카카오 계정 1",
         revenue="애드센스", daily=1, daily_note="",
         content="오래 읽히는 학습형 시리즈 (예: 자작 문제집·개념 정리). 주제는 미정",
         kpi="체류·페이지 수 (GA4)", note="옛날부터 쓴 블로그, 누적 방문 약 14,000. 관심분야(애니 등) 카테고리는 보류."),
    dict(name="눈잎", platform="tistory", status="active", address="", account="카카오 계정 1",
         revenue="애드센스", daily=1, daily_note="애드센스 승인 뒤 2편",
         content="정보성: 광고 수익(조회수) 분야 · 정책·지원금 · 블로그 수익 정리",
         kpi="검색 클릭 (서치콘솔)", note=""),
    dict(name="black_lukey", platform="naver", status="active", address="https://blog.naver.com/black_lukey",
         account="", revenue="방문자 + 쇼핑커넥트(간혹)", daily=1, daily_note="퀄리티 검증 강하게",
         content="퀄리티 있는 정보·소개 글로 방문자. 올영·무신사 행사는 조회용 소재, 쇼핑커넥트 링크는 물건 소개할 때만",
         kpi="방문자 수", note="RSS: https://rss.blog.naver.com/black_lukey.xml"),
    dict(name="블로거", platform="blogger", status="hold", address="", account="", revenue="애드센스", daily=0,
         daily_note="", content="", kpi="", note="가입·조사 중. 공식 API로 임시저장까지 올릴 수 있다 (12 문서)."),
    dict(name="워드프레스", platform="wordpress", status="hold", address="", account="", revenue="애드센스", daily=0,
         daily_note="", content="", kpi="", note="가입·조사 중. WP.com 은 유료 요금제부터 애드센스, 설치형은 호스팅 관리 (12 문서)."),
]

RULES = [
    ("common", "블로그당 하루 최대 2편, 3편 이상은 하지 않는다", "10 문서 5절"),
    ("common", "티스토리는 카카오 계정 합계 하루 3편 이하", "발행 한도가 계정 단위로 합산 (11 문서)"),
    ("common", "새 블로그·애드센스 승인 전에는 하루 1편", ""),
    ("common", "블로그 하나에 주제 축 하나", ""),
    ("common", "같은 형식 3편 연속 금지, 하루 2편이면 형식을 다르게·3시간 띄우기", ""),
    ("common", "임시저장은 주 단위로만 쌓는다 (티스토리 최대 100건·90일)", "11 문서"),
    ("check", "제목", "편당 5~10분. 하나라도 빠지면 발행하지 않는다"),
    ("check", "첫 문단", ""),
    ("check", "판단 한 줄 (이런 사람은 이것)", ""),
    ("check", "숫자·날짜를 원 출처에서 한 번 더", ""),
    ("check", "안 나온 일정은 '미정'으로", ""),
    ("naver", "방문자 수가 메인. 퀄리티 있는 글로", ""),
    ("naver", "쇼핑커넥트 링크는 물건을 소개할 때만, 참여 스마트스토어 상품만", "11 문서"),
    ("naver", "하루 10건을 넘으면 발행이 막힌다 (권장은 1편)", "사용자 보고, 공지 원문 미확인"),
    ("tistory", "AI 글 자체는 괜찮다. 가치 없는 대량 생산이면 애드센스 광고를 못 붙인다", "구글 스팸 정책"),
    ("tistory", "애드센스는 계정 단위: 한 블로그 위반이 전부에 번진다", ""),
    ("tistory", "블로그마다 주제를 다르게, 같은 틀을 동시에 쓰지 않는다", ""),
    ("ban", "자동 게시·매크로·브라우저 자동화", ""),
    ("ban", "댓글·공감 자동화 (티스토리 첫 위반 최소 7일 정지)", "티스토리 공지 2025-09"),
    ("ban", "같은 원고를 여러 블로그에", ""),
    ("ban", "남의 글·기출문제 옮기기", "큐넷 2026-07-30 저작권 공지"),
    ("ban", "안 써 본 것을 써 본 것처럼", ""),
]


def seed(apps, schema_editor):
    Blog = apps.get_model("blog_rules", "Blog")
    Rule = apps.get_model("blog_rules", "Rule")
    if not Blog.objects.exists():
        for order, data in enumerate(BLOGS, start=1):
            Blog.objects.create(order=order, **data)
    if not Rule.objects.exists():
        counters = {}
        for group, body, note in RULES:
            counters[group] = counters.get(group, 0) + 1
            Rule.objects.create(group=group, body=body, note=note, order=counters[group])


class Migration(migrations.Migration):
    dependencies = [("blog_rules", "0001_initial")]
    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
