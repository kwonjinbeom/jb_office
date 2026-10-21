"""서울·경기 분리는 글 안에서 (2026-10-21 사용자: "글 내부에서 분리되란 거야. 둘 각각 합쳐").

0012 에서 지역별로 나눈 주제를 다시 하나씩으로: 청년·신혼 정책 (서울·경기), 청약·임대주택 공고 (서울·경기).
서울 주제를 남겨 이름·지침을 바꾸고, 경기 주제의 주간 발행 기록을 옮긴 뒤 경기 주제는 휴지통으로 (지우지 않는다).
지침이 0012 가 쓴 그대로면 바꾸고, 사용자가 고쳤으면 그 글은 '기존 지침'으로 남긴다.
"""
from django.db import migrations
from django.utils import timezone

POLICY = """지역: 서울·경기만 다룬다. 한 글 안에서 '서울' · '경기' 소제목으로 나눠 쓴다 (서울 먼저). 제목에 '서울·경기'를 넣는다.
- 서울·경기 거주 청년·신혼부부가 신청할 수 있는 정책 (시·구/시·군 사업 + 중앙정부 사업 중 그 지역에서 신청하는 것). 지금 접수 중이거나 곧 열리는 것 위주.
- 정책마다: 대상(나이·소득·혼인 기간) · 지원 내용(금액) · 신청 기간 · 신청처 · 필요 서류.
- 주택 청약·임대 공고는 다루지 않는다 (따로 쓴다).
- 출처: 서울시 청년몽땅정보통 · 서울시·자치구 누리집 · 경기도 누리집 · 경기도 청년포털 · 시·군 누리집 · 복지로 · 온통청년."""

HOUSING = """지역: 서울·경기만 다룬다. 한 글 안에서 '서울' · '경기' 소제목으로 나눠 쓴다 (서울 먼저). 제목에 '서울·경기'와 '청약'·'모집공고' 같은 검색어를 넣는다.
- 아파트 청약 · 공공분양 · 임대주택(행복주택·국민임대·매입임대·전세임대 등) 모집공고. 이번 주~다음 달 접수·발표 일정.
- 공고마다: 단지·지역 · 공급 유형과 세대 수 · 신청 자격(청년·신혼·다자녀 특별공급은 표시) · 임대료/분양가 · 접수·당첨 발표 일정 · 신청처.
- 청년·신혼 지원 정책은 다루지 않는다 (따로 쓴다).
- 출처: SH 서울주택도시공사 · GH 경기주택도시공사 · LH 청약플러스 · 청약홈 · 마이홈."""

MERGE = [  # (새 이름, 서울 주제, 경기 주제, 지침)
    ("청년·신혼 정책 (서울·경기)", "청년·신혼 정책 · 서울", "청년·신혼 정책 · 경기", POLICY),
    ("청약·임대주택 공고 (서울·경기)", "청약·임대주택 공고 · 서울", "청약·임대주택 공고 · 경기", HOUSING),
]


def forward(apps, schema_editor):
    FixedTopic = apps.get_model("routines", "FixedTopic")
    TopicWeek = apps.get_model("routines", "TopicWeek")
    live = FixedTopic.objects.filter(deleted_at__isnull=True)
    for name, seoul_name, gg_name, note in MERGE:
        seoul, gg = live.filter(name=seoul_name).first(), live.filter(name=gg_name).first()
        keep = seoul or gg or live.filter(name=name).first() or FixedTopic(name=name, order=seoul and seoul.order or 3)
        old = (keep.note or "").strip()
        made = old.startswith("지역: 서울만 다룬다") or old.startswith("지역: 경기만 다룬다")  # 0012 가 쓴 지침
        if made:  # 0012 지침 아래에 붙어 있던 사용자 지침은 남긴다
            rest = old.split("기존 지침:", 1)[1].strip() if "기존 지침:" in old else ""
        else:
            rest = old if old and not old.startswith(note.splitlines()[0]) else ""
        keep.name = name
        keep.note = note + (f"\n\n기존 지침:\n{rest}" if rest else "")
        keep.save()
        if gg is not None and gg.pk != keep.pk:
            for w in TopicWeek.objects.filter(topic=gg):  # 경기 주제의 발행 표시를 합친 주제로
                tw, _ = TopicWeek.objects.get_or_create(topic=keep, week=w.week)
                if w.published and not tw.published:
                    tw.published = True
                    tw.save()
            gg.deleted_at = timezone.now()  # 휴지통으로 (지우지 않는다)
            gg.save()
    for n, topic in enumerate(live.order_by("order", "pk"), start=1):
        if topic.order != n:
            topic.order = n
            topic.save(update_fields=["order"])


class Migration(migrations.Migration):

    dependencies = [
        ("routines", "0012_topic_feedback"),
    ]

    operations = [
        migrations.RunPython(forward, migrations.RunPython.noop),
    ]
