"""사이트 타겟 바로잡기 (2026-10-22 사용자).

1. AI 소식은 일일 분량(black_lukey)이 아니라 커스텀 글쓰기의 고정 주제로, 사이트는 memorily.
   memorily 에는 애니와 이것 말고는 사용자가 따로 시키지 않는 한 글이 가지 않는다 → 글 분류 'black_lukey > AI 소식'은 휴지통으로.
2. 지금 있는 글의 사이트·분류를 새 타겟대로: 코스피는 밤밤, 정전기·전기장판(상품)은 밤밤, 밤밤에 있던 공모주·주택 공고는 눈잎 등.
   커스텀 고정 주제 중 밤밤으로 된 공모주·주택 공고도 눈잎으로.
3. memorily 의 에러 해결 글(T102 ERR_MODULE_NOT_FOUND)은 휴지통으로 (원고 폴더도 지웠다).
"""
from django.db import migrations
from django.db.models import Q
from django.utils import timezone

AI_NOTE = """매일 한 편. 사용자가 AI 최신 소식을 듣고 싶어 한다 (2026-10-22 사용자).
- 범위: 지난 24~72시간 (직전 AI 소식 원고 이후).
- 담는 것: 새로 떠오르는 AI 서비스·모델·도구, 많이 쓰는(인기·조회수 있는) AI의 업데이트 중 쓰는 사람이 체감하는 것 — 새 기능, 무료 범위·가격 변경, 성능이 크게 오름, 한국어 지원·한국 출시.
- 빼는 것: 설명할 가치가 없는 업그레이드 (버그 수정·소소한 화면 변경·이름만 바뀐 것·대기자 명단 소식뿐인 것·이미 쓴 소식·출처 없는 루머). 그런 날은 항목을 줄이고, 하나도 없으면 쓰지 않는다.
- 넓게: Claude·Codex·Genspark 는 예시일 뿐. 대화형·모델 / 코딩 / 검색·리서치 / 이미지·영상·음성·음악 / 업무·문서·회의 / 오픈소스 / 국내 AI / 폰·PC 속 AI 를 고루. 한 회사는 하루 2항목까지.
- 글 모양: 내용이 많으면 길어져도 된다. 대신 항목마다 짧게 — 소제목(서비스 이름 — 무엇이 바뀌었나) + 2~4줄(무엇이 새로·달라졌나 · 누구에게 쓸모 · 쓸 수 있는 곳·가격·날짜) + 출처 한 줄. 맨 위 인용 상자에 가장 큰 소식 한두 줄.
- 출처: 일일루틴/프롬프트/writing_sources.md 의 'AI 소식' 표."""

# 원고 제목 → (사이트, 글 분류 '사이트 > 소재', 비우면 분류 없음)
POSTS = {
    "이번 주 공모주 청약 일정 (10월 19~25일), 국내 7종목 날짜·공모가 정리": ("눈잎", "공모주"),
    "이번 주 미국 공모주(IPO) 일정 (10월 19~25일), 상장 예정은 Lycia 등 2곳": ("눈잎", "공모주"),
    "청년·신혼 정책 이번 주 (10월 19~25일): 끝난 것, 열린 것, 곧 닫히는 것": ("눈잎", "청년·신혼 정책"),
    "나루토 회차정리 애니만화 환산기 명장면 등 모음": ("memorily", ""),
    "블리치 회차정리 애니만화 환산기 명장면 등 모음": ("memorily", ""),
    "헌터×헌터 회차정리 애니만화 환산기 명장면 등 모음": ("memorily", ""),
    "원피스 회차정리 애니만화 환산기 명장면 등 모음": ("memorily", ""),
    "국내 공모주 일정 (10월 22일~12월 초), 청약·환불·상장일 종목별 정리": ("눈잎", "공모주"),
    "해외 IPO 일정 (10월 22일~11월 중순), 미국은 한산하고 홍콩 10월 28일 상장 2곳": ("눈잎", "공모주"),
    "서울·경기 청년·신혼 정책, 지금 열린 것과 다음 접수 (10월 22일 기준)": ("눈잎", "청년·신혼 정책"),
    "서울·경기 청약·임대주택 모집공고 일정 (10월 22일~11월)": ("눈잎", "주택 공고"),
    "갤럭시 One UI 9 업데이트, 내 폰은 언제 오고 지금 해도 될까 (S24·S25·S26 기종별 표)": ("black_lukey", "신제품 출시"),
    "코스피 3.29% 반등 다음 날 다시 약세, 9거래일 종가표로 보는 지금 위치": ("밤밤", "코스피"),
    "2026 월드시리즈 한국시간 일정: 10월 24일 토요일 오전 9시 개막, 어디서 볼까": ("black_lukey", "그 외"),
    "2026-27 스키장 개장일 언제? 작년 개장 순서로 보는 11~12월 달력": ("black_lukey", "축제·행사"),
    "에너지바우처 2026 신청 12월 31일까지, 우리 가족은 받을 수 있나": ("눈잎", "그 외"),
    "한국사능력검정시험 제81회 11월 28일, 접수는 11월 3일부터 — 지역별 접수 시간과 발표일": ("눈잎", "그 외"),
    "겨울 정전기 왜 심할까? 습도계 숫자부터 보고 준비물 고르는 순서 (2026)": ("밤밤", "상품 추천"),
    "전기장판 vs 온수매트 vs 탄소매트, 월 전기료 직접 계산하고 고르기 (2026 겨울)": ("밤밤", "상품 추천"),
    "11월 강릉 1박 2일 뚜벅이 코스: KTX로 가서 오죽헌·경포호·안목 바다, 뭘 미리 예약할까 (2026)": ("black_lukey", "지역 놀거리"),
    "Claude Duet 대기자 명단, 내 일 중 뭘 맡길 수 있을까 (2026-10 기준)": ("memorily", ""),
}
TRASH_TITLES = ["Error [ERR_MODULE_NOT_FOUND]: Cannot find module 해결 (Node.js 22, 윈도우 11)"]
SECTIONS = {"writing": "티스토리 글쓰기 · 임시글", "naver_writing": "네이버 글쓰기 · 임시글"}


def forward(apps, schema_editor):
    Category = apps.get_model("blog_types", "Category")
    Section = apps.get_model("blog_types", "Section")
    Placement = apps.get_model("blog_types", "Placement")
    TrashEntry = apps.get_model("core", "TrashEntry")
    FixedTopic = apps.get_model("routines", "FixedTopic")
    Blog = apps.get_model("blog_rules", "Blog")
    now = timezone.now()

    # 1. AI 소식: 커스텀 고정 주제 (memorily) + 일일 분류에서 뺌
    if not FixedTopic.objects.filter(name="AI 소식", deleted_at__isnull=True).exists():
        order = max(FixedTopic.objects.values_list("order", flat=True), default=0) + 1
        FixedTopic.objects.create(name="AI 소식", site="memorily", per_week=7, note=AI_NOTE, order=order)
    for cat in Category.objects.filter(section__name="black_lukey", name="AI 소식", deleted_at__isnull=True):
        for label in ("writing", "naver_writing"):
            apps.get_model(label, "Post").objects.filter(bt_category=cat).update(bt_category=None)
        TrashEntry.objects.filter(model_label="blog_types.category", object_key=str(cat.pk)).delete()
        TrashEntry.objects.create(model_label="blog_types.category", object_key=str(cat.pk), title=cat.name,
                                  section="카테고리 관리 · 카테고리", deleted_at=now, members={"blog_types.category": [cat.pk]})
        Category.objects.filter(pk=cat.pk).update(deleted_at=now)
    Section.objects.filter(name="black_lukey").update(note="지역 놀거리·축제 · 신제품·영화 출시 · 인기 세일 이벤트")
    Blog.objects.filter(name="black_lukey").update(content="지역 놀거리·축제 · 신제품·영화 출시 · 인기 세일")
    Blog.objects.filter(name="memorily", platform="tistory").update(content="직접 쓰는 글 (애니) · AI 소식 (커스텀) — 글쓰기 루틴 제외")
    FixedTopic.objects.filter(site="밤밤").filter(Q(name__contains="공모") | Q(name__contains="청약") | Q(name__contains="주택")).update(site="눈잎")

    # 2. 글의 사이트·분류  3. memorily 의 에러 해결 글은 휴지통으로
    cats = {(c.section.name, c.name): c for c in Category.objects.filter(deleted_at__isnull=True).select_related("section")}
    for label in ("writing", "naver_writing"):
        Post = apps.get_model(label, "Post")
        for post in Post.objects.filter(title__in=list(POSTS)):
            site, keyword = POSTS[post.title]
            cat = cats.get((site, keyword)) if keyword else None
            Post.objects.filter(pk=post.pk).update(target=site, bt_category=cat, bt_type=None, bt_sub=None)

        field = "tistory_post" if label == "writing" else "naver_post"
        for post in Post.objects.filter(title__in=TRASH_TITLES, deleted_at__isnull=True):
            places = list(Placement.objects.filter(**{field: post}, deleted_at__isnull=True).values_list("pk", flat=True))
            members = {f"{label}.post": [post.pk], **({"blog_types.placement": places} if places else {})}
            TrashEntry.objects.filter(model_label=f"{label}.post", object_key=str(post.pk)).delete()
            TrashEntry.objects.create(model_label=f"{label}.post", object_key=str(post.pk), title=post.title[:200],
                                      section=SECTIONS[label], deleted_at=now, members=members)
            Post.objects.filter(pk=post.pk).update(deleted_at=now)
            Placement.objects.filter(pk__in=places).update(deleted_at=now)


class Migration(migrations.Migration):
    dependencies = [
        ("blog_types", "0017_simple_classes"),
        ("blog_rules", "0009_site_targets"),
        ("routines", "0016_writing_by_material"),
        ("writing", "0017_clear_old_temp"),
        ("core", "0002_sourceexclusion_trashentry"),
    ]
    operations = [migrations.RunPython(forward, migrations.RunPython.noop)]
