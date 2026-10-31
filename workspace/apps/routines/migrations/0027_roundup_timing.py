"""memorily 총정리 세 갈래의 '언제 쓰나'를 유연하게 (2026-10-31 사용자: "총정리라곤 했지만 일자에 연연할 필요 없다.
중복되지 않고, 다가올 것을 사람들이 찾게 하는 것이니 유연하게").

- 무료 AI 툴: 새 툴 · 무료 범위 변경이 나오면 바로 — 1주일 만이어도, 1건이어도.
- 이달의 AI: 한 달에 한 번이 기본, 그달 정리가 없으면 날짜와 상관없이. 새 변화가 많으면 주 단위로.
- IT 할인: 다가오거나 진행 중인 행사를 찾거나 보이면 바로. 여럿이면 묶고, 하나면 하나.
기준은 날짜가 아니라 '겹치지 않나'. 고정 주제 지침(작가) · 갈래 컨셉(변환) · 0024 제목 줄의 예를 고친다.
옛 글 그대로일 때만 바꾸고, 사용자가 고쳐 옛 글이 없으면 새 '언제 쓰나' 줄만 앞에 더한다. 지우는 데이터 없음.
같은 글이 작가 파일(일일루틴/프롬프트/writing_site_memorily.md)에도 있다 — 고칠 때 둘 다.
"""
from django.db import migrations

MARK = "언제 쓰나 (2026-10-31 사용자, 날짜에 매이지 않는다)"
WHEN = {
    "무료 AI 툴": (f"- {MARK}: 새 무료 AI 툴이 나왔거나 주요 툴의 무료 범위가 바뀌면 바로 — 1주일 만이어도, 1건이어도 된다. "
               "1건이면 그 툴 하나를, 여럿이면 용도로 묶는다. 겹침만 막는다: 지난 원고(`고정주제: 무료 AI 툴`)에 같은 툴 · 같은 무료 범위가 "
               "있으면 쓰지 않고, 바뀐 것이 있으면 바뀐 것 중심으로 새 편."),
    "이달의 AI": (f"- {MARK}: 한 달에 한 번이 기본 — 그달(또는 지난달) 정리가 아직 없으면 날짜와 상관없이 쓴다. 한 달이 안 됐어도 새 변화가 "
              "많으면 주 단위로 (이번 편 `11월 1주`). 지난 원고(`고정주제: 이달의 AI`)가 다룬 기간 다음부터 — 겹치지 않게."),
    "IT 할인": (f"- {MARK}: 다가오거나 진행 중인 IT 할인 행사(광군제 · 블랙프라이데이 · 사이버먼데이 · 스팀 세일 등)를 찾거나 보이면 바로. "
              "여러 개면 한 편에 묶고, 하나면 하나만. 끝난 행사는 쓰지 않는다. 같은 행사 회차는 한 번 — 쿠폰 · 기간이 새로 확정되면 그 원고를 고친다. "
              "기기 · 주변기기 · 소프트웨어 · 게임만 — 브랜드 세일 한 회차는 black_lukey › 세일 이벤트."),
}
OLD_NOTES = {  # routines 0023 의 '언제 쓰나' 줄
    "무료 AI 툴": "- 용도 하나(이미지 · 영상 · PPT · 글쓰기 · 코딩 · 음성)를 골라 그 용도의 무료 AI 툴을 총정리한다. "
               "같은 용도는 30일 안에 다시 쓰지 않는다 (지난 원고의 `고정주제: 무료 AI 툴`).",
    "이달의 AI": "- 매월 1~3일에만 지난달 것을 쓴다. 그 밖의 날은 글감 없음.",
    "IT 할인": "- 날짜가 정해진 IT 할인 행사(광군제 11.11 · 블랙프라이데이 · 사이버먼데이 · 스팀 세일 등)가 오늘부터 10일 안에 시작할 때만. 아니면 글감 없음.\n"
              "- 같은 행사는 한 해 한 번 (큰 변화가 있으면 그 원고를 고친다). 기기 · 주변기기 · 소프트웨어 · 게임만 — 브랜드 세일 한 회차는 black_lukey › 세일 이벤트.",
}
CONCEPT_SWAPS = {  # blog_types 0054 갈래 컨셉의 첫 줄
    "무료 AI 툴": [("마다 돈 안 내고 어디까지 되는지 총정리.",
                "마다 돈 안 내고 어디까지 되는지 총정리. 새 툴 · 무료 범위 변경이 나오면 바로, 1건이어도 된다 (날짜에 매이지 않는다).")],
    "이달의 AI": [("한 달 동안 바뀐 AI를 한 편에 (매월 1~3일, 지난달).",
               "한 달 동안 바뀐 AI를 한 편에 (한 달에 한 번이 기본, 새 변화가 많으면 주 단위 — 날짜에 매이지 않고 이미 정리한 기간과 겹치지 않게).")],
    "IT 할인": [("IT 할인 행사를 한 편에 (행사 7~10일 전).",
              "IT 할인 행사를 찾거나 보이면 바로 정리 (여러 개면 한 편에 묶고 하나면 하나만, 끝난 행사는 쓰지 않는다 — 날짜에 매이지 않는다).")],
}
TITLE_SWAPS = [  # routines 0024 제목 줄의 '이번 편'
    ("이달의 AI 총정리 · <그달 (2026년 10월)>", "이달의 AI 총정리 · <그달 또는 주 (2026년 10월 · 11월 1주)>"),
    ("무료 AI 툴 총정리 · <용도 (PPT · 영상 · 이미지 …)>", "무료 AI 툴 총정리 · <용도 또는 툴 (PPT · 영상 · 새 툴 이름 …)>"),
    ("IT 할인 총정리 · <행사 (광군제 · 블랙프라이데이 …)>", "IT 할인 총정리 · <행사 하나 또는 묶음 (광군제 · 블랙프라이데이 …)>"),
]


def note_for(name, note):
    old = OLD_NOTES[name]
    if MARK in note:
        new = note
    elif old in note:
        new = note.replace(old, WHEN[name])
    else:
        new = (WHEN[name] + "\n" + note).strip()
    for a, b in TITLE_SWAPS:
        new = new.replace(a, b)
    return new


def concept_for(name, concept):
    new = concept
    for a, b in CONCEPT_SWAPS[name]:
        new = new.replace(a, b)
    for a, b in TITLE_SWAPS:
        new = new.replace(a, b)
    return new


def forward(apps, schema_editor):
    FixedTopic = apps.get_model("routines", "FixedTopic")
    SiteCategory = apps.get_model("blog_types", "SiteCategory")
    for topic in FixedTopic.objects.filter(name__in=WHEN, deleted_at__isnull=True):
        new = note_for(topic.name, topic.note)
        if new != topic.note:
            topic.note = new
            topic.save(update_fields=["note"])
    for cat in SiteCategory.objects.filter(blog__name="memorily", name__in=WHEN, deleted_at__isnull=True):
        new = concept_for(cat.name, cat.concept)
        if new != cat.concept:
            cat.concept = new
            cat.save(update_fields=["concept"])


class Migration(migrations.Migration):
    dependencies = [("routines", "0026_followups")]
    operations = [migrations.RunPython(forward, migrations.RunPython.noop)]
