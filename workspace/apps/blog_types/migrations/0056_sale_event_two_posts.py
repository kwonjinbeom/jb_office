"""black_lukey › 세일 이벤트: 고정 5곳은 한 회차를 한 번 더 써도 된다 (2026-10-31 사용자: "공개예정일을 미리 알리는 것과
실제로 공식 글이 떴을 때 2번 알리는 것도 충분히 괜찮다" — 올영 블프 T236 은 예고, 본 행사 공개 뒤 본 공개 글).
0055 컨셉의 고정 5곳 줄 뒤에 한 줄을 더한다. 이미 있거나 그 줄이 없으면(사람이 고침) 두고 알린다. 지우는 데이터 없음.
같은 글이 작가 파일(writing_site_black_lukey.md)·소재 판정(writing_topics.md)에도 있다 — 고칠 때 모두.
"""
from django.db import migrations

NAME = "세일 이벤트"
ANCHOR = "공식 공지한 한 회차를 한 편에 (시작 7~10일 전 ~ 진행 첫 주)."
ADDED = ("공식 공지한 한 회차를 한 편에 (시작 7~10일 전 ~ 진행 첫 주). 기간만 먼저 뜨면 미리 알리고, 할인·쿠폰·상품이 "
         "공식으로 뜨면 그 내용으로 한 편 더 써도 된다 (미공개 칸은 '본 행사 페이지에서 공개', 지어내지 않는다).")


def forward(apps, schema_editor):
    SiteCategory = apps.get_model("blog_types", "SiteCategory")
    for sc in SiteCategory.objects.filter(blog__name="black_lukey", parent=None, name=NAME, deleted_at__isnull=True):
        if ANCHOR in sc.concept:
            sc.concept = sc.concept.replace(ANCHOR, ADDED, 1)
            sc.save(update_fields=["concept"])
        elif "한 편 더 써도 된다" not in sc.concept:
            print(f"\n  blog_types 0056: black_lukey › {NAME} 컨셉을 사람이 고쳐서 그대로 둠")


class Migration(migrations.Migration):
    dependencies = [("blog_types", "0055_sale_event_by_search")]
    operations = [migrations.RunPython(forward, migrations.RunPython.noop)]
