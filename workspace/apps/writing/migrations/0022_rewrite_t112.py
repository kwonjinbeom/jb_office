"""'11월 교토 단풍' 글을 새 눈잎 › 일본 여행 컨셉으로 다시 쓴 글로 바꾼다 (2026-10-23 사용자: 지금 이 프롬으로 완전히 바꿔서, 지역·주제를 바꿔도 된다).

원고: 콘텐츠/블로그_카페/포스팅자동화/원고/T112_오사카3박4일/원고.md (11월 오사카 3박 4일 — 교토 단풍·나라까지 난바 거점).
옛 제목의 글(임시글·검토글·발행예정글 어디든)의 제목·본문·태그·소개를 새 원고로 바꾸고, 넣은 곳이 있으면 변환을 '미변환'으로 돌린다
(옛 변환본은 남지만 새 글로 다시 변환해야 한다). 원고 파일이 없으면 아무것도 하지 않는다.
"""
from django.conf import settings
from django.db import migrations

OLD_TITLE = "11월 교토 단풍 언제 가면 덜 붐빌까? 주차별 달력과 엔화 나눠 바꾸기"
DRAFT = ("콘텐츠", "블로그_카페", "포스팅자동화", "원고", "T112_오사카3박4일", "원고.md")


def forward(apps, schema_editor):
    from apps.writing.drafts import parse

    path = settings.REPO_ROOT.joinpath(*DRAFT)
    if not path.is_file():
        return
    draft = parse(path.read_text(encoding="utf-8"), DRAFT[-2])
    if draft is None:
        return
    Placement = apps.get_model("blog_types", "Placement")
    for label, field in (("writing", "tistory_post"), ("naver_writing", "naver_post")):
        Post = apps.get_model(label, "Post")
        for post in Post.objects.filter(title=OLD_TITLE):
            Post.objects.filter(pk=post.pk).update(title=draft.title, body=draft.body, tags=draft.tags, summary=draft.summary)
            Placement.objects.filter(**{field: post}).update(convert_status="none")


class Migration(migrations.Migration):
    dependencies = [
        ("writing", "0021_mha_wording"),
        ("naver_writing", "0008_post_planned_on"),
        ("blog_types", "0022_nunip_japan_concept"),
    ]
    operations = [migrations.RunPython(forward, migrations.RunPython.noop)]
