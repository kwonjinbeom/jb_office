"""memorily › 애니 제목 규칙: 검색 질문형이되 그 작품에만 있는 말로 (2026-10-28 사용자: 이누야샤·슬램덩크 제목이 또 형식적이다 — 세 번째).

0005 의 질문형 틀 `<작품> <질문>? 화수 환산기·…` 만 남아, 작품 이름만 바꾸면 어디에나 맞는 제목이 나왔다.
- 카테고리 컨셉의 제목 줄을 새 규칙으로 바꾼다 (0005 가 넣은 말이 있을 때. 없으면 끝에 붙인다).
- 발행 전인 슬램덩크·이누야샤 글 제목을 원고와 같게 고친다 (글 · 넣은 곳의 변환 제목). 원고 지문도 새 제목으로 맞춰
  글 관리를 열 때 '수정됨'·미변환으로 돌지 않게 한다. 지우는 데이터 없음.
"""
import hashlib

from django.db import migrations

OLD_RULE = ("제목은 검색 질문형 (2026-10-26): `<작품> <자동완성에서 가장 많이 묻는 질문>? 화수 환산기·<보는 순서 · 극장판 순서 · 오리지널 회차 중 1~2개>` "
            "— 예 `블리치 천년혈전은 만화 몇 화부터? 화수 환산기와 오리지널 스킵 회차`. '회차정리 애니만화 환산기 명장면 등 모음' 같은 나열 제목은 쓰지 않는다.")
NEW_RULE = "제목은 검색 질문형이되 **그 작품에만 있는 말로 묻는다** (2026-10-28 사용자: 작품 이름만 바꾸면 어느 작품에나 맞는 제목은 형식적이다). 2번 자동완성에서 그 작품만의 편·시리즈·사건 이름(무한성편 · 땅울림 · Z·카이·슈퍼·GT · 3기 · 천년혈전 · 완결편 · 산왕전 같은 것)을 골라 질문에 넣는다: `<작품> <그 말이 든 질문>? 화수 환산기·<그 작품에 맞는 것 1~2개 (보는 순서 · 극장판 순서 · 오리지널 회차 · 명장면 몇 화)>` — 좋은 예 (발행한 글) `귀멸의 칼날 무한성편은 만화 몇 권부터? 화수 환산기와 극장판까지 보는 순서` · `진격의 거인 총 몇 화, 몇 기까지? 화수 환산기·보는 순서·땅울림 몇 화` · `드래곤볼 보는 순서 Z·카이·슈퍼·GT, 애니 몇 화가 만화 몇 권? 화수 환산기`. 쓰지 않는 예 `슬램덩크 애니 몇 화까지 만화 몇 권? 화수 환산기·극장판 순서` (작품 이름만 바꾸면 어디에나 맞는다). 그 작품에 없는 것을 묻지 않고 (몇 기로 나뉘지 않은 작품에 '몇 기'), 제목이 묻는 것에 본문 소제목이 답한다. '회차정리 애니만화 환산기 명장면 등 모음' 같은 나열 제목도 쓰지 않는다."
TITLES = [
    ("슬램덩크 애니 몇 화까지 만화 몇 권? 화수 환산기·극장판 순서",
     "슬램덩크 애니 101화 다음은 만화 몇 권부터? 화수 환산기·산왕전과 더 퍼스트 슬램덩크"),
    ("이누야샤 몇 기 몇 화까지 만화 몇 권? 화수 환산기·극장판 순서와 완결편",
     "이누야샤 167화 다음 완결편은 만화 몇 권부터? 화수 환산기·극장판 순서"),
]


def _sig(title, body, tags, summary):  # writing.views.draft_sig 와 같다 (칸 사이는 \x1f)
    return hashlib.sha1("\x1f".join((title, body, tags, summary)).encode("utf-8")).hexdigest()


def forward(apps, schema_editor):
    SiteCategory = apps.get_model("blog_types", "SiteCategory")
    Placement = apps.get_model("blog_types", "Placement")
    Post = apps.get_model("writing", "Post")
    for cat in SiteCategory.objects.filter(blog__name="memorily", name__startswith="애니", deleted_at__isnull=True):
        if "그 작품에만 있는 말로 묻는다" in cat.concept:
            continue
        cat.concept = cat.concept.replace(OLD_RULE, NEW_RULE) if OLD_RULE in cat.concept else cat.concept.rstrip() + "\n- " + NEW_RULE
        cat.save(update_fields=["concept"])
    try:  # 같은 커밋의 새 원고 (서버는 pull 뒤에 migrate 한다) — 글 관리의 원고 동기화가 보는 지문 그대로
        from apps.writing import drafts
        by_title = {d.title: d for d in drafts.list_drafts()}
    except Exception:
        by_title = {}
    for old, new in TITLES:
        d = by_title.get(new)
        for post in Post.objects.filter(title=old):
            post.title = new
            if d and post.source:
                post.source_sig = _sig(d.title, d.body, d.tags, d.summary)
            post.save(update_fields=["title", "source_sig"])
        Placement.objects.filter(converted_title=old).update(converted_title=new)


class Migration(migrations.Migration):
    dependencies = [
        ("anime", "0005_concept_question_title"),
        ("blog_types", "0048_wordpress_drop_asof_line"),
        ("writing", "0026_trash_nunip_kospi"),
    ]
    operations = [migrations.RunPython(forward, migrations.RunPython.noop)]
