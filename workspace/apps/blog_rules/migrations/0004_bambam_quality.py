"""2026-10-16 사용자 결정.

- 구글 블로거 = **밤밤**, 정보성 글. 블로그끼리 내용이 겹치는 글은 올리지 않는다: Claude 원고를 블로그마다 나눠 배정.
- 정보성 품질 순서: 눈잎(티스토리) > 밤밤(블로거).
- 워드프레스는 마지막에 사용자와 상세히 정한다.

화면에서 이미 고친 값은 건드리지 않는다 (처음 값 그대로일 때만 바꾼다). 규칙은 같은 문장이 없을 때만 더한다.
"""
from django.db import migrations

OLD_BLOGGER_NOTE = "가입 완료. 하루 편수·주제는 정하는 중. 공식 API로 임시저장까지 올릴 수 있다 (12 문서)."
OLD_WP_NOTE = "가입·조사 중. WP.com 은 유료 요금제부터 애드센스, 설치형은 호스팅 관리 (12 문서)."

RULES = [
    ("common", "블로그끼리 내용이 겹치는 글은 올리지 않는다 (원고를 블로그마다 나눠 배정)", "2026-10-16 사용자"),
    ("common", "정보성 품질 순서: 눈잎(티스토리) > 밤밤(블로거). 가장 공들인 원고는 눈잎에", "2026-10-16 사용자"),
]


def forward(apps, schema_editor):
    Blog = apps.get_model("blog_rules", "Blog")
    Rule = apps.get_model("blog_rules", "Rule")
    blogger = Blog.objects.filter(platform="blogger").first()
    if blogger:
        if blogger.name == "블로거":
            blogger.name = "밤밤"
        if not blogger.content:
            blogger.content = "정보성 (눈잎과 겹치지 않게 나눠 배정, 품질은 눈잎 다음)"
        if not blogger.kpi:
            blogger.kpi = "검색 클릭 (서치콘솔)"
        if blogger.note == OLD_BLOGGER_NOTE:
            blogger.note = "하루 편수는 정하는 중. 공식 API로 임시저장까지 올릴 수 있다 (12 문서)."
        blogger.save()
    nunip = Blog.objects.filter(name="눈잎").first()
    if nunip and not nunip.note:
        nunip.note = "정보성 1순위: 가장 공들인 원고는 여기 (밤밤과 겹치지 않게)."
        nunip.save()
    wp = Blog.objects.filter(platform="wordpress").first()
    if wp and wp.note == OLD_WP_NOTE:
        wp.note = "마지막에 사용자와 상세히 정한다 (요금제·설치형·용도). 참고: 12 문서."
        wp.save()
    order = Rule.objects.filter(group="common").count()
    for group, body, note in RULES:
        if not Rule.objects.filter(body=body).exists():
            order += 1
            Rule.objects.create(group=group, body=body, note=note, order=order)


class Migration(migrations.Migration):
    dependencies = [("blog_rules", "0003_memorily_it_blogger")]
    operations = [migrations.RunPython(forward, migrations.RunPython.noop)]
