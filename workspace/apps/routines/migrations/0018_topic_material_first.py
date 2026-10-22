"""커스텀 글쓰기 지침 3차 (2026-10-22 사용자).

1. AI 소식: 핵심 AI 도구의 근황. 정말 괜찮은 소식이면 한 편에 여럿 녹인다. 아주 새 기능을 써 본 사람들의 후기가 있으면 적당히 풀어 준다.
2. 청년·신혼 정책 · 청약·임대주택 공고: 날짜가 지난 것을 또 쓰지 않는다. 새로 쓸 게 없으면 원고를 만들지 않는다 (글감 없음).
   (모든 고정 주제에 같은 규칙이 안내문에도 붙는다 — topics.topic_text.)
지침이 이전 migration 이 쓴 문장 그대로면 그 문장을 바꾸고, 사용자가 고쳐 문장이 없으면 맨 아래 '추가 지침'으로 붙인다. 지우는 데이터 없음.
"""
from django.db import migrations

ADDED = "추가 지침 (2026-10-22):"

AI_REPLACE = [
    ("- 담는 것: 새로 떠오르는 AI 서비스·모델·도구, 많이 쓰는(인기·조회수 있는) AI의 업데이트 중 쓰는 사람이 체감하는 것 — 새 기능, 무료 범위·가격 변경, 성능이 크게 오름, 한국어 지원·한국 출시.",
     "- 담는 것: 핵심 AI 도구의 근황 — 사람들이 실제로 많이 쓰는 도구(ChatGPT·Codex, Claude·Claude Code, Gemini, Cursor, Perplexity, Genspark, Midjourney 등)의 업데이트 중 쓰는 사람이 체감하는 것: 새 기능, 무료 범위·가격 변경, 성능이 크게 오름, 한국어 지원·한국 출시. 새로 떠오르는 서비스·모델은 화제가 확실할 때만."),
    ("그런 날은 항목을 줄이고, 하나도 없으면 쓰지 않는다.",
     "그런 날은 항목을 줄이고, 하나도 없으면 원고를 만들지 않는다 (글감 없음)."),
    ("- 넓게: Claude·Codex·Genspark 는 예시일 뿐. 대화형·모델 / 코딩 / 검색·리서치 / 이미지·영상·음성·음악 / 업무·문서·회의 / 오픈소스 / 국내 AI / 폰·PC 속 AI 를 고루. 한 회사는 하루 2항목까지.",
     "- 핵심 도구가 먼저, 살피기는 넓게: 대화형·모델 / 코딩 / 검색·리서치 / 이미지·영상·음성·음악 / 업무·문서·회의 / 오픈소스 / 국내 AI / 폰·PC 속 AI 를 두루 살피되, 싣는 것은 많이 쓰는 도구의 의미 있는 변화부터. 한 회사는 한 편에 2항목까지."),
]
AI_ADD = [
    "- 한 편에 여럿: 정말 괜찮은 소식이면 편을 나누지 않고 한 편에 여러 항목을 녹인다. 괜찮은 게 하나뿐이면 하나만.",
    "- 써 본 사람들 후기: 아주 새 기능·모델을 실제로 써 본 사람들의 후기(Reddit · X · Hacker News · GeekNews · 커뮤니티 · 리뷰 영상)가 있으면 "
    "그 항목 안에 2~3줄로 적당히 풀어 준다 — 무엇을 해 봤고, 어디가 좋았고, 어디서 막혔는지. 우리 경험처럼 쓰지 않고 '써 본 사람들은 …'으로, "
    "출처 줄에 그 글 주소. 후기가 없으면 억지로 넣지 않는다.",
]

POLICY_REPLACE = [
    (" (마감된 지 일주일이 안 된 것만 '방금 마감' 한 줄은 된다)", ""),
    ("- 해당하는 게 적거나 없으면 억지로 채우지 않는다. 있는 것만 짧게 쓰고, 원고 제작 정보 '각도' 칸에 '접수 중 N건 · 예정 N건'을 적는다 (발행할지는 사용자가 정한다).",
     "- 지금 접수 중이거나 앞으로 열리는 게 없거나, 지난 원고와 같은 정책뿐이고 새로 열린 게 없으면 원고를 만들지 않는다 (글감 없음). 있으면 있는 것만 짧게, 원고 제작 정보 '각도' 칸에 '접수 중 N건 · 예정 N건'."),
]
POLICY_ADD = ["- 쓰기 직전에 정책마다 신청 기간 끝 날짜를 오늘과 다시 대조한다. 끝난 것은 '방금 마감'으로도 넣지 않는다."]

HOUSING_REPLACE = [
    ("접수가 이미 끝난 공고는 넣지 않는다.",
     "접수가 이미 끝난 공고는 넣지 않는다. 남은 공고가 없거나 지난 원고와 같은 공고뿐이면 원고를 만들지 않는다 (글감 없음)."),
]
HOUSING_ADD = ["- 쓰기 직전에 공고마다 접수 마감일을 오늘과 다시 대조한다. 끝난 공고는 표에서도 뺀다."]

TOPICS = [
    ("AI 소식", AI_REPLACE, AI_ADD),
    ("청년·신혼 정책 (서울·경기)", POLICY_REPLACE, POLICY_ADD),
    ("청약·임대주택 공고 (서울·경기)", HOUSING_REPLACE, HOUSING_ADD),
]


def update(note, replace, add):
    """바꿀 문장이 있으면 바꾸고 더할 줄은 바꾼 줄 바로 아래에. 없으면(사용자가 고친 지침) 맨 아래 '추가 지침'으로."""
    note = note.rstrip()
    missing, anchor = [], None
    for old, new in replace:
        if new and new in note:
            anchor = new
            continue
        if old in note:
            note = note.replace(old, new, 1)
            anchor = new or anchor
        elif new:
            missing.append(new)
    lines = [line for line in add if line not in note]
    if anchor and not missing:
        if lines:
            at = note.index(anchor)
            end = note.find("\n", at)
            end = len(note) if end < 0 else end
            note = note[:end] + "\n" + "\n".join(lines) + note[end:]
        return note
    lines = [line for line in missing + lines if line not in note]
    if not lines:
        return note
    if ADDED not in note:
        note += f"\n\n{ADDED}"
    return note + "\n" + "\n".join(lines)


def forward(apps, schema_editor):
    FixedTopic = apps.get_model("routines", "FixedTopic")
    for name, replace, add in TOPICS:
        for topic in FixedTopic.objects.filter(name=name, deleted_at__isnull=True):
            note = update(topic.note or "", replace, add)
            if note != (topic.note or ""):
                topic.note = note
                topic.save(update_fields=["note"])


class Migration(migrations.Migration):
    dependencies = [("routines", "0017_ai_news_one")]
    operations = [migrations.RunPython(forward, migrations.RunPython.noop)]
