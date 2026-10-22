"""글 분류를 '사이트 > 고정 소재' 두 단으로 줄인다 (2026-10-22 사용자).

사용자: 글 분류는 거의 다 미분류로 두고 손대지 않는다. 너무 세세하니 거의 다 지우고 간략한 키워드만.
쓰다 보니 사이트마다 방향이 잡혔으니 글쓰기 결과물의 타겟을 확실히 — 사이트마다 고정 소재를 두고 '그 외' 하나씩.
글 분류는 글쓰기의 컨셉으로 쓰인다 (사이트 카테고리 컨셉은 변환 때). 이 안에서 AI 가 자유롭게 고쳐도 된다.

- 지금 살아 있는 대분류(판매 수익·광고 수익·IT/AI 등)는 그 아래 중·소·하위와 함께 휴지통으로 (7일 안에 복원할 수 있다).
- 새 대분류 = 글쓰기 루틴이 쓰는 사이트: 눈잎 · black_lukey · 밤밤. 티스토리 memorily 는 사용자가 직접 쓰니 두지 않는다.
- 그 아래 고정 소재(중분류)만, 소분류 없음. 방향 칸 = 글쓰기 컨셉. 소재가 있는 날만 쓴다 (routines.views.default_picks).
- 옛 중분류가 붙은 글은 가장 가까운 새 소재로 옮긴다 (소·하위는 비운다).
"""
from django.db import migrations
from django.utils import timezone

OTHER = ("그 외", "위 소재 말고 이 사이트 방향에 맞는 강한 소재가 있을 때만", "")
SECTIONS = [
    ("눈잎", "주택 공고 · 청년·신혼 정책 · 공모주 · 엔화 · 일본 중심 해외여행 알짜 정보", [
        ("주택 공고", "새 공고의 자격·소득 기준·접수일을 표로. 커스텀 글이 다룬 범위 밖 새 공고만", "나도 넣을 수 있나, 언제 접수하지"),
        ("청년·신혼 정책", "새로 열린 신청·바뀐 기준을 대상·금액·마감으로", "나도 받나, 언제까지 신청하지"),
        ("공모주", "새 종목·일정 변경·수요예측 결과처럼 커스텀 글에 없는 새 소식", "이번 공모주 넣을까, 언제 청약하지"),
        ("엔화·환율", "엔화 중심. 지금 환율의 위치와 환전 방법·수수료 계산", "지금 바꿔도 되나, 어디서 바꾸지"),
        ("일본 여행", "일본 여행의 바뀐 제도·항공·패스·면세·축제 일정을 알짜로", "이번에 일본 가면 뭘 알아야 하지"),
        ("해외 여행", "일본 외 해외의 입국 규정·항공권·환율·시즌 정보를 알짜로", "거기 가려면 뭘 준비하지"),
        OTHER,
    ]),
    ("black_lukey", "지역 놀거리·축제 · 신제품·영화 출시 · 인기 세일 이벤트 · AI 소식", [
        ("지역 놀거리", "어느 지역 한 곳의 당일치기·코스·볼거리. 지역을 매번 바꾼다", "이번 주말 어디 가지"),
        ("축제·행사", "열리기 전 축제·전시·행사의 날짜·장소·가는 법·덜 붐비는 때", "언제 가면 좋지"),
        ("신제품 출시", "아이폰·갤럭시 등 최신 기기·제품의 공개일·사전예약·가격·달라진 점", "언제 나오고 뭐가 달라졌지"),
        ("영화·OTT 공개", "개봉·공개 예정작을 볼지 말지 고를 수 있게", "이번 주 뭐 보지"),
        ("세일 이벤트", "올영·무신사·유니클로 등 인기 세일의 기간·혜택·살 만한 것", "언제 하고 뭘 사면 좋지"),
        ("AI 소식", "새로 뜨는 AI와 많이 쓰는 AI의 의미 있는 업데이트를 한 편에 모아, 항목마다 짧은 요약", "요즘 AI 뭐가 새로 나왔고 뭐가 바뀌었지"),
        OTHER,
    ]),
    ("밤밤", "코스피·나스닥 그날 움직인 이유 · 가끔 상품 추천", [
        ("코스피", "그날 코스피가 오르내린 이유를 종가·수치와 함께 (한국 거래일만)", "오늘 코스피 왜 이래"),
        ("나스닥", "간밤 나스닥이 오르내린 이유를 종가·수치와 함께 (미국 거래일만)", "어젯밤 나스닥 왜 이래"),
        ("상품 추천", "고르는 기준·비교표·사람 유형별 추천 (가끔, 시즌 소재가 있을 때)", "뭘 사야 하지"),
        OTHER,
    ]),
]

# 옛 중분류 → 새 (대분류, 소재)
MOVE = {
    "문제 해결": ("밤밤", "상품 추천"), "고르기": ("밤밤", "상품 추천"), "타이밍": ("black_lukey", "세일 이벤트"),
    "선물": ("밤밤", "상품 추천"), "비용 계산": ("밤밤", "상품 추천"), "생활 장면": ("밤밤", "상품 추천"),
    "여행·체험": ("black_lukey", "지역 놀거리"), "여행·계절": ("black_lukey", "축제·행사"),
    "금융·시장": ("밤밤", "코스피"), "정책·내 돈": ("눈잎", "청년·신혼 정책"), "생활 일정·요금": ("눈잎", "그 외"),
    "콘텐츠·엔터": ("black_lukey", "영화·OTT 공개"), "스포츠 일정": ("black_lukey", "그 외"),
    "IT·앱": ("black_lukey", "신제품 출시"), "시험·교육": ("눈잎", "그 외"),
    "AI 도구·활용": ("black_lukey", "AI 소식"), "개발·코딩": ("black_lukey", "그 외"),
    "IT 소식·제품": ("black_lukey", "신제품 출시"),
}


def forward(apps, schema_editor):
    Section = apps.get_model("blog_types", "Section")
    Category = apps.get_model("blog_types", "Category")
    PostType = apps.get_model("blog_types", "PostType")
    SubType = apps.get_model("blog_types", "SubType")
    TrashEntry = apps.get_model("core", "TrashEntry")
    RoutinePick = apps.get_model("routines", "RoutinePick")
    now = timezone.now()

    old = list(Section.objects.filter(deleted_at__isnull=True))
    if any(s.name == "눈잎" for s in old):
        return
    new_cats = {}
    start = max([s.order for s in old], default=0) + 1
    for i, (name, note, cats) in enumerate(SECTIONS):
        section = Section.objects.create(name=name, note=note, order=start + i)
        for j, (cname, direction, question) in enumerate(cats):
            new_cats[(name, cname)] = Category.objects.create(
                section=section, code=chr(65 + j), name=cname, direction=direction, question=question, order=j + 1)

    moved = {}
    for s in old:
        cats = list(Category.objects.filter(section=s, deleted_at__isnull=True))
        types = list(PostType.objects.filter(category__in=cats, deleted_at__isnull=True))
        subs = list(SubType.objects.filter(post_type__in=types, deleted_at__isnull=True))
        for c in cats:
            if c.name in MOVE:
                moved[c.pk] = new_cats[MOVE[c.name]]
        members = {"blog_types.section": [s.pk], "blog_types.category": [c.pk for c in cats],
                   "blog_types.posttype": [t.pk for t in types], "blog_types.subtype": [x.pk for x in subs]}
        members = {k: v for k, v in members.items() if v}
        TrashEntry.objects.filter(model_label="blog_types.section", object_key=str(s.pk)).delete()
        TrashEntry.objects.create(model_label="blog_types.section", object_key=str(s.pk), title=s.name[:200],
                                  section="카테고리 관리 · 대분류", deleted_at=now, members=members)
        for model, rows in ((Section, [s]), (Category, cats), (PostType, types), (SubType, subs)):
            model.objects.filter(pk__in=[r.pk for r in rows]).update(deleted_at=now)

    for label in ("writing", "naver_writing"):
        Post = apps.get_model(label, "Post")
        for post in Post.objects.filter(bt_category__in=list(moved)):
            Post.objects.filter(pk=post.pk).update(bt_category=moved[post.bt_category_id], bt_type=None, bt_sub=None)
    RoutinePick.objects.filter(day__gte=timezone.localdate()).delete()  # 옛 분류로 고른 오늘·앞날 분량은 기본으로


class Migration(migrations.Migration):
    dependencies = [
        ("blog_types", "0016_placement_converted_check"),
        ("core", "0002_sourceexclusion_trashentry"),
        ("routines", "0015_topic_feedback_titles"),
        ("writing", "0016_post_custom"),
        ("naver_writing", "0007_post_custom"),
    ]
    operations = [migrations.RunPython(forward, migrations.RunPython.noop)]
