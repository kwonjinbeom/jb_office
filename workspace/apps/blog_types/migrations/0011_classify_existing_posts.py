"""2026-10-16 사용자: 임시 템플릿에 이미 있는 글에 분류를 정해 넣는다.

실서버 글 제목(10-16 확인)으로 찾고, 아직 미분류인 글만 바꾼다 (화면에서 정한 분류는 그대로).
분류는 이름으로 찾는다: (대분류, 카테고리 기호, 타입, 하위). 없으면 건너뛴다.
'저장만 하고 다시 안 본 것들은 숙제였을까'(고찰 글)는 맞는 분류가 없어 미분류로 둔다.
"""
from django.db import migrations

SALES, VIEWS = "판매 수익 (커넥트)", "광고 수익 (조회수)"

TISTORY = {
    "독감 무료접종 일정, 올해는 왜 빨라졌을까? 우리 집 나이별로 정리": (VIEWS, "B", "대상·신청일 (내 줄 찾기)", None),
    "직접 담그기·절임배추·사 먹는 김치, 올해 우리 집은 뭐가 맞을까": (SALES, "E", "사는 게 나은지 비교", None),
    "레더 재킷·트렌치·스웨이드, 이번 가을 한 벌만 산다면 뭐가 맞을까": (SALES, "B", "A vs B", None),
    "에버랜드·롯데월드·성수 짱구 전시, 할로윈 주말엔 누구와 가느냐로 골라요": (VIEWS, "H", "축제·개장 달력", None),
    "롤 몰라도 롤드컵이 재밌어지는 법, 화면 위 숫자부터 읽기 (2026 일정·한국 팀)": (VIEWS, "E", "대회 일정 + 입문", None),
    "수능보다 바쁜 49일, 2027 수능 다음 날부터 정시 원서까지 한 장에": (VIEWS, "G", "시험 달력", None),
}
NAVER = {
    "가습기 4L면 밤새 쓸까? 물통 용량·가습량으로 구매 전 계산하는 법": (SALES, "B", "기준 정리", None),
    "외장 SSD T7·T9 차이: 2000MB/s 사기 전 포트·케이블 확인법": (SALES, "B", "A vs B", "두 개만 비교"),
}


def _node(apps, section, code, type_name, sub_name):
    Category = apps.get_model("blog_types", "Category")
    cat = Category.objects.filter(section__name=section, code=code, deleted_at__isnull=True,
                                  section__deleted_at__isnull=True).first()
    if cat is None:
        return None
    t = cat.types.filter(name=type_name, deleted_at__isnull=True).first() if type_name else None
    if type_name and t is None:
        return (cat, None, None)
    s = t.subs.filter(name=sub_name, deleted_at__isnull=True).first() if sub_name and t else None
    return (cat, t, s)


def forward(apps, schema_editor):
    for app, table in (("writing", TISTORY), ("naver_writing", NAVER)):
        Post = apps.get_model(app, "Post")
        for title, where in table.items():
            node = _node(apps, *where)
            if node is None:
                continue
            Post.objects.filter(title=title, bt_category__isnull=True, deleted_at__isnull=True).update(
                bt_category=node[0], bt_type=node[1], bt_sub=node[2])


class Migration(migrations.Migration):
    dependencies = [
        ("blog_types", "0010_placement"),
        ("writing", "0005_post_bt_category_post_bt_sub_post_bt_type"),
        ("naver_writing", "0003_post_bt_category_post_bt_sub_post_bt_type"),
    ]
    operations = [migrations.RunPython(forward, migrations.RunPython.noop)]
