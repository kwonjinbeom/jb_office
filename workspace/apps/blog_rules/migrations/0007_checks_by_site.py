"""규칙 화면을 사이트 중심으로 (2026-10-16 사용자: "일반적인 다 알고 있는 규칙은 필요 없다.
각 사이트를 올리면서 까먹을 수 있는 것, 체크할 것만").

1. 사이트에 붙지 않은 예전 일반 규칙(처음 넣은 것들)을 **휴지통으로** 옮긴다. 휴지통 화면에서 7일 동안 복원할 수 있다
   (core.trash.move_to_trash 와 같은 방식: deleted_at + TrashEntry).
2. 사이트마다 체크를 넣는다. 그 사이트에 체크가 이미 있으면 넣지 않는다.
3. 체크로 옮긴 카드 메모(black_lukey 편수 메모)를 비우고, 컨셉은 한 줄로 줄인다. 처음 값 그대로일 때만.
"""
from django.db import migrations
from django.utils import timezone

CHECKS = {
    "memorily": [
        "눈잎과 같은 카카오 계정: 둘 합쳐 하루 3편 이하",
        "애드센스는 블로그마다 따로 승인",
        "관심분야(애니 등) 카테고리는 보류",
    ],
    "눈잎": [
        "밤밤과 주제·내용 겹치지 않게 (원고 나눠 배정)",
        "가장 공들인 정보성 원고는 여기",
        "memorily와 합쳐 하루 3편 이하",
        "애드센스 승인 확인 → 하루 2편으로",
    ],
    "black_lukey": [
        "쇼핑커넥트 링크는 참여 스마트스토어 상품만",
        "올영·무신사 행사는 조회용 소재 (링크 없음)",
        "숫자·날짜는 원 출처에서 한 번 더 (퀄리티 검증)",
        "RSS 공개 설정 확인 (지금 공개 글 0편)",
    ],
    "밤밤": [
        "눈잎과 주제·내용 겹치지 않게",
        "품질은 눈잎 다음",
        "하루 편수 정하기",
    ],
    "워드프레스": [
        "요금제·설치형·용도는 마지막에 사용자와 정함",
    ],
}

# 컨셉: 예전 값 그대로일 때만 짧게 (겹치지 않게·품질 순서 같은 건 체크로 옮겼다)
CONCEPTS = {
    "memorily": ("IT 기반: 개발·AI 정보 등 (개발자 관점, 오래 읽히는 정리 글)", "IT·개발·AI 정보 (개발자 관점 정리 글)"),
    "눈잎": ("정보성: 광고 수익(조회수) 분야 · 정책·지원금 · 블로그 수익 정리", "정보성 1순위: 정책·지원금·수익 정리"),
    "black_lukey": ("퀄리티 있는 정보·소개 글로 방문자. 올영·무신사 행사는 조회용 소재, 쇼핑커넥트 링크는 물건 소개할 때만",
                    "방문자 수: 퀄리티 정보·소개 글"),
    "밤밤": ("정보성 (눈잎과 겹치지 않게 나눠 배정, 품질은 눈잎 다음)", "정보성 2순위: 눈잎과 다른 주제"),
    "워드프레스": ("", "미정"),
}


def forward(apps, schema_editor):
    Blog = apps.get_model("blog_rules", "Blog")
    Rule = apps.get_model("blog_rules", "Rule")
    TrashEntry = apps.get_model("core", "TrashEntry")
    now = timezone.now()
    for rule in Rule.objects.filter(blog__isnull=True, deleted_at__isnull=True):
        if TrashEntry.objects.filter(model_label="blog_rules.rule", object_key=str(rule.pk)).exists():
            continue
        TrashEntry.objects.create(model_label="blog_rules.rule", object_key=str(rule.pk), title=rule.body[:200],
                                  section="규칙", deleted_at=now, members={"blog_rules.rule": [rule.pk]})
        rule.deleted_at = now
        rule.save(update_fields=["deleted_at"])
    for name, bodies in CHECKS.items():
        blog = Blog.objects.filter(name=name, deleted_at__isnull=True).first()
        if blog is None or Rule.objects.filter(blog=blog, deleted_at__isnull=True).exists():
            continue
        for order, body in enumerate(bodies, start=1):
            Rule.objects.create(blog=blog, body=body, order=order)
    Blog.objects.filter(name="black_lukey", daily_note="퀄리티 검증 강하게").update(daily_note="")
    for name, (old, new) in CONCEPTS.items():
        Blog.objects.filter(name=name, content=old).update(content=new)


class Migration(migrations.Migration):
    dependencies = [("blog_rules", "0006_site_checks"), ("core", "0002_sourceexclusion_trashentry")]
    operations = [migrations.RunPython(forward, migrations.RunPython.noop)]
