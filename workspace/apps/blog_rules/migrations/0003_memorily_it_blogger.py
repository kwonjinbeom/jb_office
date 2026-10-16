"""2026-10-16 사용자 정정.

- memorily: 학습형 시리즈(자작 문제집) 대신 **IT 기반** (사용자가 개발자: 개발·AI 정보 등).
- 블로거: 주소가 생겼다 (https://bambam2222.blogspot.com/). 상태는 '준비' (하루 편수는 아직 정하지 않음).

화면에서 이미 고친 값은 건드리지 않는다: 처음 넣은 값 그대로일 때만 바꾼다.
"""
from django.db import migrations

OLD_MEMORILY = "오래 읽히는 학습형 시리즈 (예: 자작 문제집·개념 정리). 주제는 미정"
NEW_MEMORILY = "IT 기반: 개발·AI 정보 등 (개발자 관점, 오래 읽히는 정리 글)"
OLD_BLOGGER_NOTE = "가입·조사 중. 공식 API로 임시저장까지 올릴 수 있다 (12 문서)."
NEW_BLOGGER_NOTE = "가입 완료. 하루 편수·주제는 정하는 중. 공식 API로 임시저장까지 올릴 수 있다 (12 문서)."


def forward(apps, schema_editor):
    Blog = apps.get_model("blog_rules", "Blog")
    Blog.objects.filter(name="memorily", content=OLD_MEMORILY).update(content=NEW_MEMORILY)
    blogger = Blog.objects.filter(platform="blogger", address="").first()
    if blogger:
        blogger.address = "https://bambam2222.blogspot.com/"
        if blogger.status == "hold":
            blogger.status = "ready"
        if blogger.note == OLD_BLOGGER_NOTE:
            blogger.note = NEW_BLOGGER_NOTE
        blogger.save()


class Migration(migrations.Migration):
    dependencies = [("blog_rules", "0002_seed")]
    operations = [migrations.RunPython(forward, migrations.RunPython.noop)]
