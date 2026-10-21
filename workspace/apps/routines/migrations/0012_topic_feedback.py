"""커스텀 글쓰기 주제별 피드백 (2026-10-21 사용자).

1. 청년·신혼 정책과 주택 공고는 따로 둔다 → '청약·임대주택 공고' 주제를 새로 (검색에 잘 걸리는 말: 청약 · 임대주택 · 모집공고).
2. 정책·주택 공고는 서울과 경기만, 서울·경기를 나눠 쓴다 → 주제를 지역별로 나눈다 (예전 '청년·신혼 정책'은 '· 서울'로 이름만 바꾼다).
3·4. 공모주(국내·해외)는 앞으로 한 달 또는 분기 일정, 사람들이 눈여겨보는 상장은 최대한 많이.
지침이 이미 있으면 지우지 않고 아래에 '기존 지침'으로 남긴다. 지우는 데이터 없음.
"""
from django.db import migrations

IPO_KR = """다루는 기간: 앞으로 한 달 (일정이 몰려 있지 않으면 분기까지). 이번 주에 확정된 것만이 아니라 다가올 일정을 미리 정리한다.
- 국내 공모주: 수요예측 · 일반 청약 · 환불 · 상장일을 종목별로. 사람들이 눈여겨보는 상장(대형·화제 종목, 유명 기업 자회사, 대어급)은 빠짐없이, 그 밖의 종목도 최대한 많이 적는다. 스팩은 스팩이라고 표시.
- 종목마다: 업종 한 줄, 공모가 범위(확정되면 확정가), 주관사, 청약 증권사, 일정. 확정 공모가·기관 경쟁률이 나온 종목은 그 숫자.
- 출처: 38커뮤니케이션 공모주 일정 · DART 증권신고서 · 한국거래소 KIND 신규상장. 투자 권유 표현은 쓰지 않는다.
- 지난 글과 겹치는 종목은 바뀐 것(확정가·경쟁률·일정 변경)만 짚고 새 종목 위주로."""

IPO_US = """다루는 기간: 앞으로 한 달 (일정이 몰려 있지 않으면 분기까지). 다가올 일정을 미리 정리한다.
- 해외 IPO: 미국(나스닥·NYSE) 중심, 홍콩·일본 등 대형 상장도. 국내 투자자가 눈여겨보는 상장(빅테크·AI·유명 브랜드·대어급)은 빠짐없이, 그 밖의 종목도 최대한 많이 적는다.
- 종목마다: 회사 한 줄 소개, 거래소 · 티커 · 상장 예정일 · 공모가 범위(확정되면 확정가) · 공모 규모, 국내 증권사 앱에서 언제부터 거래 가능한지.
- 출처: Nasdaq · NYSE IPO 캘린더 · SEC S-1/F-1 · Renaissance Capital. 날짜는 한국 시간도 함께. 투자 권유 표현은 쓰지 않는다.
- 지난 글과 겹치는 종목은 바뀐 것(일정 연기·가격 확정)만 짚고 새 종목 위주로."""


def policy(region, other, sources):
    return f"""지역: {region}만 다룬다 ({other} 쪽은 따로 쓴다). 제목에 지역명({region})을 넣는다.
- {region} 거주 청년·신혼부부가 신청할 수 있는 정책 (시·구/시·군 사업 + 중앙정부 사업 중 {region}에서 신청하는 것). 지금 접수 중이거나 곧 열리는 것 위주.
- 정책마다: 대상(나이·소득·혼인 기간) · 지원 내용(금액) · 신청 기간 · 신청처 · 필요 서류.
- 주택 청약·임대 공고는 다루지 않는다 (따로 쓴다).
- 출처: {sources} · 복지로 · 온통청년."""


def housing(region, other, sources):
    return f"""지역: {region}만 다룬다 ({other} 쪽은 따로 쓴다). 제목에 지역명({region})과 '청약'·'모집공고' 같은 검색어를 넣는다.
- {region} 아파트 청약 · 공공분양 · 임대주택(행복주택·국민임대·매입임대·전세임대 등) 모집공고. 이번 주~다음 달 접수·발표 일정.
- 공고마다: 단지·지역 · 공급 유형과 세대 수 · 신청 자격(청년·신혼·다자녀 특별공급은 표시) · 임대료/분양가 · 접수·당첨 발표 일정 · 신청처.
- 청년·신혼 지원 정책은 다루지 않는다 (따로 쓴다).
- 출처: {sources} · 청약홈 · 마이홈."""


TOPICS = [  # (이름, 예전 이름, 지침)
    ("공모주 일정 · 국내", None, IPO_KR),
    ("공모주 일정 · 해외", None, IPO_US),
    ("청년·신혼 정책 · 서울", "청년·신혼 정책", policy("서울", "경기", "서울시 청년몽땅정보통 · 서울시 누리집 · 자치구 누리집")),
    ("청년·신혼 정책 · 경기", None, policy("경기", "서울", "경기도 누리집 · 경기도 청년포털 · 시·군 누리집")),
    ("청약·임대주택 공고 · 서울", None, housing("서울", "경기", "SH 서울주택도시공사 · LH 청약플러스(서울)")),
    ("청약·임대주택 공고 · 경기", None, housing("경기", "서울", "GH 경기주택도시공사 · LH 청약플러스(경기)")),
]


def forward(apps, schema_editor):
    FixedTopic = apps.get_model("routines", "FixedTopic")
    live = FixedTopic.objects.filter(deleted_at__isnull=True)
    for order, (name, old, note) in enumerate(TOPICS, start=1):
        topic = live.filter(name=name).first() or (live.filter(name=old).first() if old else None)
        if topic is None:
            topic = FixedTopic(name=name)
        topic.name = name
        topic.order = order
        mine = (topic.note or "").strip()
        if note.splitlines()[0] not in mine:
            topic.note = note + (f"\n\n기존 지침:\n{mine}" if mine else "")
        topic.save()
    for n, topic in enumerate(live.exclude(name__in=[t[0] for t in TOPICS]).order_by("order", "pk"), start=len(TOPICS) + 1):
        topic.order = n  # 사용자가 따로 추가한 주제는 뒤로
        topic.save(update_fields=["order"])


class Migration(migrations.Migration):

    dependencies = [
        ("routines", "0011_fixed_topics"),
    ]

    operations = [
        migrations.RunPython(forward, migrations.RunPython.noop),
    ]
