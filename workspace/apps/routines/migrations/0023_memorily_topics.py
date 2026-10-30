"""글쓰기 자동화의 memorily (2026-10-31 사용자: "분기 신작 글쓰기 자동화에 안 넣어? 카테고리명 IT·AI 로 바꿨다고 했잖아").

사이트 카테고리처럼 글쓰기 자동화에서도 계층으로: memorily > IT·AI > 고정 주제 넷 · memorily > 애니 > 분기 신작.
1. 글 분류 memorily › AI → IT·AI (사이트 카테고리 이름과 같게). 아래 고정 주제 AI 소식은 그대로.
2. 총정리 셋(blog_types 0052 가 글 분류 소재로 만든 것)은 IT·AI 아래 고정 주제로 — 주제마다 지침(언제 쓰나 · 넣을 곳)이 따로라 기획 없이 작가에게 바로.
   옛 소재 셋은 그 소재로 분류된 글이 없을 때만 휴지통으로.
3. 글 분류 memorily › 애니 소재를 만들고 그 아래 고정 주제 '분기 신작'.
넣을 곳은 blog_types.sites.TOPIC_PLACES (memorily › IT·AI › 갈래 · memorily › 애니 › 분기 신작). 글 모양은 일일루틴/프롬프트/writing_site_memorily.md.
지우는 데이터 없음 (휴지통은 되살릴 수 있다).
"""
import re

from django.db import migrations
from django.utils import timezone

IT_AI = "IT·AI"
DOC = "글 모양 · 그림은 `일일루틴/프롬프트/writing_site_memorily.md` 의 '{part}'."
TOPICS = [  # (주제, 소재, 지침)
    ("무료 AI 툴", IT_AI, "\n".join([
        "- 용도 하나(이미지 · 영상 · PPT · 글쓰기 · 코딩 · 음성)를 골라 그 용도의 무료 AI 툴을 총정리한다. 같은 용도는 30일 안에 다시 쓰지 않는다 (지난 원고의 `고정주제: 무료 AI 툴`).",
        "- 무료 범위 · 요금은 오늘 각 서비스 요금 페이지에서 다시 확인한다. 확인 못 한 한도는 쓰지 않는다.",
        "- 넣을 카테고리: memorily › IT·AI › 무료 AI 툴. " + DOC.format(part="무료 AI 툴"),
    ])),
    ("이달의 AI", IT_AI, "\n".join([
        "- 매월 1~3일에만 지난달 것을 쓴다. 그 밖의 날은 글감 없음.",
        "- 재료: 그달 AI 소식 원고(원고 폴더에서 `고정주제: AI 소식`) + 공식 발표. 날마다 쓴 말을 옮기지 않고 '무엇이 가장 컸나 · 나는 뭘 바꾸면 되나'로 묶는다.",
        "- 넣을 카테고리: memorily › IT·AI › 이달의 AI. " + DOC.format(part="이달의 AI"),
    ])),
    ("IT 할인", IT_AI, "\n".join([
        "- 날짜가 정해진 IT 할인 행사(광군제 11.11 · 블랙프라이데이 · 사이버먼데이 · 스팀 세일 등)가 오늘부터 10일 안에 시작할 때만. 아니면 글감 없음.",
        "- 같은 행사는 한 해 한 번 (큰 변화가 있으면 그 원고를 고친다). 기기 · 주변기기 · 소프트웨어 · 게임만 — 브랜드 세일 한 회차는 black_lukey › 세일 이벤트.",
        "- 넣을 카테고리: memorily › IT·AI › IT 할인. " + DOC.format(part="IT 할인"),
    ])),
    ("분기 신작", "애니", "\n".join([
        "- 다음 분기(1 · 4 · 7 · 10월) 시작 3주 전부터 시작 뒤 1주까지만. 그 밖은 글감 없음. 같은 분기는 한 번 (새로 확정된 작품이 많으면 그 원고를 고친다).",
        "- 그 분기 신작 애니를 사용자가 쓰는 애니 글처럼 평범하게 — 환산기 짜임 · 주제 그림 없이. 제목에 '분기'를 넣는다.",
        "- 방영작은 공식 발표로 확인하고 확정 · 예정을 나눠 적는다.",
        "- 넣을 카테고리: memorily › 애니 › 분기 신작. " + DOC.format(part="분기 신작"),
    ])),
]
OLD_CATS = ("무료 AI 툴", "이달의 AI", "IT 할인")  # blog_types 0052 가 글 분류 소재로 만든 것


def _bare(name):
    return re.sub(r"\s+", "", name or "")


def forward(apps, schema_editor):
    Section = apps.get_model("blog_types", "Section")
    Category = apps.get_model("blog_types", "Category")
    FixedTopic = apps.get_model("routines", "FixedTopic")
    section = Section.objects.filter(name="memorily", deleted_at__isnull=True).first()
    if section is None:
        return
    live = Category.objects.filter(section=section, deleted_at__isnull=True)

    it_ai = next((c for c in live if _bare(c.name) in ("AI", _bare(IT_AI))), None)
    if it_ai is None:
        it_ai = Category.objects.create(section=section, code="A", name=IT_AI, order=1)
    it_ai.name = IT_AI
    it_ai.direction = "AI 소식과 총정리(무료 AI 툴 · 이달의 AI · IT 할인)를 고정 주제로"
    it_ai.question = "요즘 AI·IT 뭐가 새로 나왔고 뭐가 바뀌었지"
    it_ai.save()

    anime = next((c for c in live if c.name.startswith("애니")), None)
    if anime is None:
        order = max(live.values_list("order", flat=True), default=0) + 1
        anime = Category.objects.create(section=section, code="B", name="애니", order=order,
                                        direction="애니 글 — 회차정리는 애니 총정리 화면, 분기 신작은 고정 주제로",
                                        question="이번 분기 애니 뭐 하지")

    order = max(FixedTopic.objects.values_list("order", flat=True), default=0)
    for name, cat_name, note in TOPICS:
        if FixedTopic.objects.filter(name=name, deleted_at__isnull=True).exists():
            continue
        order += 1
        FixedTopic.objects.create(name=name, site="memorily", category=it_ai if cat_name == IT_AI else anime,
                                  note=note, order=order)

    Post = apps.get_model("writing", "Post")
    NaverPost = apps.get_model("naver_writing", "Post")
    for c in live.filter(name__in=OLD_CATS):
        if not (Post.objects.filter(bt_category=c).exists() or NaverPost.objects.filter(bt_category=c).exists()):
            Category.objects.filter(pk=c.pk).update(deleted_at=timezone.now())


class Migration(migrations.Migration):
    dependencies = [
        ("routines", "0022_drop_other"),
        ("blog_types", "0054_memorily_branches"),
        ("writing", "0027_posts_plan_day"),
        ("naver_writing", "0008_post_planned_on"),
    ]
    operations = [migrations.RunPython(forward, migrations.RunPython.noop)]
