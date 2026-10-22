"""고정 주제를 소재 아래로 + 눈잎·밤밤 소재 정리 (2026-10-23 사용자).

- 고정 주제는 글 분류의 소재 아래에 있다: 공모주 일정 국내·해외 → 눈잎 > 공모주, 청년·신혼 정책 → 눈잎 > 청년·신혼 정책,
  청약·임대주택 공고 → 눈잎 > 주택 공고 (FixedTopic.category).
- 지침은 소재의 방향(새 공고·새 종목·새로 열린 신청)을 앞세우고 기존 지침을 그 뒤에 둔다 (사용자: 소재 쪽 말이 더 맞다, 섞되 그걸 우선).
- 눈잎의 일본은 한 소재: 엔화·환율 · 일본 여행 · 일본의 흥미로운 소식 전부 → '일본'. 엔화·환율 소재는 일본으로 합치고
  (붙은 글은 일본으로 옮긴 뒤) 휴지통으로 — 7일 안에 복원할 수 있다.
- 해외여행은 밤밤으로: 해외의 가볼 만한 곳·흥미로운 주제 (네이버 black_lukey 의 국내 지역 놀거리처럼). 눈잎에 남은 해외 여행 소재는
  밤밤으로 옮기고, 밤밤에 이미 있으면(사용자가 만들었으면) 그쪽으로 글을 옮긴 뒤 휴지통으로.
- 서버에서 이미 바꿔 둔 것은 건너뛴다 (이름이 맞는 것만 손댄다). 사이트 컨셉 문구는 처음 넣은 값일 때만 바꾼다.
"""
from django.db import migrations, models
import django.db.models.deletion
from django.utils import timezone

OVERSEAS = ("해외 여행", "해외여행")
JAPAN_DIRECTION = "일본에 관한 알짜 정보 전부 — 엔화·환율(지금 위치·환전) · 일본 여행(제도·항공·패스·면세·축제) · 일본의 흥미로운 소식"
JAPAN_QUESTION = "지금 엔화 바꿔도 되나, 이번에 일본 가면 뭘 알아야 하지"
OVERSEAS_DIRECTION = "해외의 가볼 만한 곳·흥미로운 주제 — 나라·도시 한 곳의 코스·볼거리·가는 법 (black_lukey 지역 놀거리의 해외판, 매번 다른 곳)"
OVERSEAS_QUESTION = "이번에 해외 어디 가 볼까"
OLD_OVERSEAS_DIRECTION = "일본 외 해외의 입국 규정·항공권·환율·시즌 정보를 알짜로"
SECTION_NOTE = {
    "눈잎": "주택 공고 · 청년·신혼 정책 · 공모주 · 일본(엔화·여행·일본 소식) 알짜 정보",
    "밤밤": "코스피·나스닥 그날 움직인 이유 · 해외여행 가볼 만한 곳 · 가끔 상품 추천",
}
BLOG_CONTENT = {  # blog_rules 0009 의 값 그대로일 때만
    "눈잎": ("주택 공고 · 청년·신혼 정책 · 공모주 · 엔화 · 일본 중심 해외여행 알짜",
             "주택 공고 · 청년·신혼 정책 · 공모주 · 일본(엔화·여행·일본 소식) 알짜"),
    "밤밤": ("코스피·나스닥 그날 이유 (각각) · 가끔 상품 추천",
             "코스피·나스닥 그날 이유 (각각) · 해외여행 가볼 만한 곳 · 가끔 상품 추천"),
}

# 고정 주제 → 소재, 지침 맨 앞에 붙일 방향 (소재의 방향이 먼저)
MARK = "방향 (우선):"
TOPICS = {
    "공모주 일정 · 국내": ("공모주", "방향 (우선): 새 종목 · 일정 변경 · 수요예측 결과처럼 지난 글에 없던 새 소식이 먼저다. "
                       "독자의 질문은 '이번 공모주 넣을까, 언제 청약하지'. 새 소식이 없으면 원고를 만들지 않는다 (글감 없음)."),
    "공모주 일정 · 해외": ("공모주", "방향 (우선): 새 종목 · 상장일 변경 · 공모가 확정처럼 지난 글에 없던 새 소식이 먼저다. "
                       "독자의 질문은 '이번 해외 공모주 볼까, 언제 상장하지'. 새 소식이 없으면 원고를 만들지 않는다 (글감 없음)."),
    "청년·신혼 정책 (서울·경기)": ("청년·신혼 정책", "방향 (우선): 새로 열린 신청 · 바뀐 기준을 대상 · 금액 · 마감으로. "
                                "독자의 질문은 '나도 받나, 언제까지 신청하지'."),
    "청약·임대주택 공고 (서울·경기)": ("주택 공고", "방향 (우선): 새 공고의 자격 · 소득 기준 · 접수일을 표로. "
                                  "독자의 질문은 '나도 넣을 수 있나, 언제 접수하지'."),
}
HOUSING_ITEM = ("신청 자격(청년·신혼·다자녀 특별공급은 표시)", "신청 자격·소득 기준(청년·신혼·다자녀 특별공급은 표시)")


def _active(Category, section, names):
    return Category.objects.filter(section=section, name__in=names, deleted_at__isnull=True).order_by("order", "pk").first()


def _merge(apps, source, target, now):
    """source 소재에 붙은 글·고정 주제를 target 으로 옮기고 source 를 휴지통으로."""
    Category = apps.get_model("blog_types", "Category")
    for label in ("writing", "naver_writing"):
        apps.get_model(label, "Post").objects.filter(bt_category=source).update(bt_category=target, bt_type=None, bt_sub=None)
    apps.get_model("routines", "FixedTopic").objects.filter(category=source).update(category=target)
    TrashEntry = apps.get_model("core", "TrashEntry")
    TrashEntry.objects.filter(model_label="blog_types.category", object_key=str(source.pk)).delete()
    TrashEntry.objects.create(model_label="blog_types.category", object_key=str(source.pk), title=f"{source.section.name} › {source.name}"[:200],
                              section="카테고리 관리 · 카테고리", deleted_at=now, members={"blog_types.category": [source.pk]})
    Category.objects.filter(pk=source.pk).update(deleted_at=now)


def _renumber(Category, section):
    """기호 A, B, C … 와 순서를 다시 매긴다. '그 외'는 맨 뒤."""
    cats = sorted(Category.objects.filter(section=section, deleted_at__isnull=True), key=lambda c: (c.name == "그 외", c.order, c.pk))
    for i, c in enumerate(cats):
        Category.objects.filter(pk=c.pk).update(code=chr(65 + i), order=i + 1)


def forward(apps, schema_editor):
    Section = apps.get_model("blog_types", "Section")
    Category = apps.get_model("blog_types", "Category")
    Blog = apps.get_model("blog_rules", "Blog")
    FixedTopic = apps.get_model("routines", "FixedTopic")
    now = timezone.now()
    nunip = Section.objects.filter(name="눈잎", deleted_at__isnull=True).first()
    bam = Section.objects.filter(name="밤밤", deleted_at__isnull=True).first()

    if nunip:  # 일본은 한 소재
        japan = _active(Category, nunip, ["일본"]) or _active(Category, nunip, ["일본 여행"]) or _active(Category, nunip, ["엔화·환율"])
        if japan:
            Category.objects.filter(pk=japan.pk).update(name="일본", direction=JAPAN_DIRECTION, question=JAPAN_QUESTION)
            for name in ("일본 여행", "엔화·환율"):
                other = _active(Category, nunip, [name])
                if other and other.pk != japan.pk:
                    _merge(apps, other, japan, now)
    if nunip and bam:  # 해외여행은 밤밤으로
        old = _active(Category, nunip, OVERSEAS)
        new = _active(Category, bam, OVERSEAS)
        if old and new:
            _merge(apps, old, new, now)
        elif old:
            Category.objects.filter(pk=old.pk).update(section=bam, order=90)
            new = Category.objects.get(pk=old.pk)
        if new and (not new.direction.strip() or new.direction == OLD_OVERSEAS_DIRECTION):
            Category.objects.filter(pk=new.pk).update(direction=OVERSEAS_DIRECTION, question=new.question or OVERSEAS_QUESTION)
    for section in (nunip, bam):
        if section:
            _renumber(Category, section)
            Section.objects.filter(pk=section.pk).update(note=SECTION_NOTE[section.name])
    for name, (old_text, new_text) in BLOG_CONTENT.items():
        Blog.objects.filter(name=name, content=old_text).update(content=new_text)

    for name, (material, head) in TOPICS.items():
        for topic in FixedTopic.objects.filter(name=name, deleted_at__isnull=True):
            cat = _active(Category, nunip, [material]) if nunip else None
            note = topic.note
            if MARK not in note:
                note = f"{head}\n{note}".strip()
            note = note.replace(*HOUSING_ITEM)
            FixedTopic.objects.filter(pk=topic.pk).update(category=cat or topic.category, note=note, site=topic.site or "눈잎")


class Migration(migrations.Migration):
    dependencies = [
        ("routines", "0019_topics_on_nunip"),
        ("blog_types", "0019_nunip_site_categories"),
        ("blog_rules", "0009_site_targets"),
        ("writing", "0020_anime_fma_mha"),
        ("naver_writing", "0008_post_planned_on"),
        ("core", "0004_menu_groups"),
    ]
    operations = [
        migrations.AddField(
            model_name="fixedtopic",
            name="category",
            field=models.ForeignKey(
                blank=True, help_text="글 분류의 소재. 커스텀 글쓰기에서 그 소재 아래에 보이고 원고 분류가 된다", null=True,
                on_delete=django.db.models.deletion.SET_NULL, related_name="fixed_topics", to="blog_types.category", verbose_name="소재"),
        ),
        migrations.RunPython(forward, migrations.RunPython.noop),
    ]
