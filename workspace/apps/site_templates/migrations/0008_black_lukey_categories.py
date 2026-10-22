"""2026-10-23 사용자 피드백 (네이버 black_lukey 발행 글 강릉·경주·넷플릭스·갤럭시): 카테고리마다 글 모양을 아주 자세히.

1. black_lukey 사이트 템플릿: 구성·꼭 지킬 것 — 정보 카드, 사진 620 가운데, 링크 자리 금지, 네이버 지도.
2. black_lukey 카테고리 컨셉: 지역 놀거리 · 축제·행사 · 영화·OTT 공개 · 출시 (비어 있을 때만 채운다).
   같은 글이 원고 체크리스트(일일루틴/프롬프트/writing_checklist.md '소재별 글 모양')에도 있다 — 고칠 때 둘 다.
3. 잘못 넣은 매핑 바로잡기: 갤럭시 S27 글 축제·행사 → 출시, 넷플릭스 공개작 글 일상 → 영화·OTT 공개 (네이버에는 맞게 올라가 있다).
사이트 템플릿은 0007 의 값 그대로일 때만 바꾼다.
"""
from django.db import migrations

OLD = dict(tone="소개·정보 해요체, 짧은 문단, 가벼운 이모티콘 조금.", structure="",
           rules="쇼핑커넥트 링크는 참여 스마트스토어 상품만, 대가 문구는 첫 부분.")
NEW = dict(
    tone="소개·정보 해요체, 짧은 문단, 가벼운 이모티콘 조금.",
    structure="\n".join([
        "카테고리 컨셉의 '글 모양'을 그대로 따른다 (지역 놀거리·축제·행사 / 영화·OTT 공개 / 출시는 글 모양이 정해져 있다).",
        "공통: 맨 위 인용 상자(결론 1~3문장) → 본문 → 마무리 서술 2~4문장 → 참고 출처 한 줄.",
        "갈 곳·맛집·작품·제품의 시간·요금·출연·스펙 같은 정보는 문장으로 풀지 않고 정보 카드(::: 장소|맛집|작품|제품 | 이름 … :::)로 짧게.",
    ]),
    rules="\n".join([
        "사진은 모두 너비 620 · 가운데 (포스터는 300). Pexels·Unsplash 주소는 w=620.",
        "링크 자리([예약 링크 자리 …])를 남기지 않는다. 기차표·입장권·예매·작품 페이지는 실제 주소를 끝까지 건다. 걸 곳이 없으면 그 줄을 지운다.",
        "쇼핑커넥트 링크는 실제 참여 스마트스토어 상품 링크가 있을 때만, 대가 문구는 첫 부분.",
        "갈 곳·맛집에는 네이버 지도 장소 링크 (https://map.naver.com/p/entry/place/<번호>).",
    ]),
)

CARD_HOW = ("정보 카드 쓰는 법: 한 줄에 `이모지 이름표 | 값`, 위아래 `::: 종류 | 이름` 과 `:::`. "
            "값 안에 [글](주소) 링크를 쓸 수 있다. 서버가 색 있는 두 칸 표로 그린다 (시간표 표와 다른 디자인).")

PLACE = "\n".join([
    "글 모양 (2026-10-23 사용자 — 강릉·경주 코스 글 피드백):",
    "- 길이: 짧게 줄이지 않는다. 갈 곳마다 사진·설명·정보 카드를 다 넣어서 길어져도 된다.",
    "- 순서: 맨 위 인용 상자(결론) → 공감 한 줄 → 하루 시간표 표(시간·동선·예약하면 편한 것) → 갈 곳마다 소제목 → 맛집·카페(선택) → 마무리.",
    "- 갈 곳마다 (`## 1. 장소: 한 줄 포인트`):",
    "  ① 사진 1장 이상 — 그 장소가 실제로 찍힌 사진, 가로 우선, 너비 620 가운데.",
    "  ② 서술형 코멘트 2~4문장: 어떤 곳인지 · 무엇을 보는지 · 언제 가면 좋은지 · 팁.",
    "  ③ 정보 카드 `::: 장소 | 정식 이름` — 서술하지 않고 단답: ⏰ 관람 시간 · 🚪 입장(매표) 마감 · 💳 입장료(어른·청소년·어린이·무료 대상) · "
    "📅 휴무 · 🎫 예약(예약 사이트 링크 · 예약이 없으면 '현장 매표' + 공식 안내 링크) · 🚌 가는 법(역·버스·도보 몇 분) · "
    "🅿️ 주차(주차장 이름·요금 + 네이버 지도 링크) · 📍 지도(네이버 지도 장소 링크) · 그 밖에 이곳만의 것(야간 개장·혼잡 시간·포토 스폿 등). "
    "무료·상시 개방인 곳도 카드를 넣는다 (입장료 무료, 시간 상시).",
    "- 맛집·카페 (의무 아님): 동선 위의 정말 유명한 곳만 1~3곳 (후기·지도로 확인). 짧은 설명 1~2문장 + `::: 맛집 | 이름` "
    "(🍽️ 대표 메뉴·가격 · ⏰ 영업·휴무 · 📍 지도) + 사진이 있으면 1장. 가 본 척하지 않는다.",
    "- 링크: 예약 링크 자리를 남기지 않는다. 기차표는 코레일(https://www.letskorail.com), 입장권·체험은 공식 예약 페이지나 실제 예매처 주소를 끝까지 건다.",
    "- 지도: 모든 갈 곳에 네이버 지도 장소 링크. 차로 오는 사람이 많은 곳은 주차장 링크도, 주차장이 마땅치 않으면 관광지 자체로.",
    "- 빼는 것: '이런 분께 맞아요'(맞는 분/맞지 않는 분 표), '숙소는 어디에 잡을까' 같은 숙소 고르기 단락.",
    "- 마무리: 표·목록 없이 서술형 2~4문장. 이 코스의 어느 곳에서 무엇을 즐기면 좋은지(풍경·배움·맛)를 짚고 잘 다녀오라는 인사. '도움이 되셨길' 같은 상투어 금지.",
    CARD_HOW,
])
FESTIVAL = PLACE.replace("강릉·경주 코스 글 피드백", "지역 놀거리와 같은 모양").replace(
    "🚪 입장(매표) 마감", "📅 기간·🚪 입장 마감").replace("하루 시간표 표(시간·동선·예약하면 편한 것)", "일정 표(기간·장소·요금)")
OTT = "\n".join([
    "글 모양 (2026-10-23 사용자 — 넷플릭스 공개작 글 피드백, 지금 글은 대부분 좋다):",
    "- 순서: 맨 위 인용 상자 → 한눈에 보는 공개 일정 표(공개일·작품·종류·길이) → 작품마다 소제목 → '뭐부터 볼까' 표(선택) → 마무리 한두 문장.",
    "- 작품마다 (`## 작품 이름 · 공개일`):",
    "  ① 공식 포스터 1장 — 작게 고정(너비 300) · 가운데, 다음 줄 `*포스터: 넷플릭스*` 처럼 출처.",
    "  ② 서술형 2~4문장: 어떤 이야기인지 · 볼 포인트 · 누구에게 맞는지 (스포 없이).",
    "  ③ 정보 카드 `::: 작품 | 제목` — 🎬 종류·장르 · 📅 공개(요일·한국시간) · 📺 볼 곳(OTT + 작품 페이지 링크) · "
    "⏱️ 러닝타임 또는 회차·공개 방식 · 🔞 관람 등급 · 🎥 감독·연출 · 👥 주요 출연(배역) · 🏆 화제·수상(있으면) · ▶️ 예고편 링크(있으면). "
    "위 일정 표에 있는 공개일·길이도 카드에 한 번 더 적는다.",
    CARD_HOW,
])
LAUNCH = "\n".join([
    "글 모양 (2026-10-23 사용자 — 갤럭시 S27 출시일 글 피드백, 짜임이 좋다):",
    "- 지금 짜임을 유지한다: 맨 위 결론 → 지난 일정 표 → 지금 알려진 것(확인·소문·믿지 않아도 되는 것) → 지금 살까 기다릴까 → 공식 소식 보는 곳.",
    "- 사진을 3~5장으로 늘린다: 제품 실물·공개 행사·전작. 폰만이 아니라 태블릿·노트북·게임기·가전·자동차 같은 모든 최신 기기에 같다. 너비 620 가운데.",
    "- 스펙 비교표를 넣는다: 전작들과 신제품(소문이면 '소문' 표시) — 칩셋·화면·카메라·배터리·충전·무게·출고가처럼 그 기기를 고르는 기준이 되는 칸.",
    "- 제품 정보 카드 `::: 제품 | 이름` (선택): 📅 공개·사전예약·출시 · 💳 출고가 · 🛒 사전예약·구매 페이지 링크 · 🔧 핵심 스펙.",
    CARD_HOW,
])
CONCEPTS = {"지역 놀거리": PLACE, "축제·행사": FESTIVAL, "영화·OTT 공개": OTT, "출시": LAUNCH}

MOVES = {  # 글 제목 앞부분 → 바른 카테고리 (black_lukey)
    "갤럭시 S27 언제 나올까?": "출시",
    "11월 넷플릭스 한국 공개작 3편": "영화·OTT 공개",
}


def forward(apps, schema_editor):
    SiteTemplate = apps.get_model("site_templates", "SiteTemplate")
    SiteCategory = apps.get_model("blog_types", "SiteCategory")
    Placement = apps.get_model("blog_types", "Placement")
    SiteTemplate.objects.filter(blog__name="black_lukey", **OLD).update(**NEW)
    cats = {c.name: c for c in SiteCategory.objects.filter(blog__name="black_lukey", parent=None, deleted_at__isnull=True)}
    for name, concept in CONCEPTS.items():
        if name in cats and not cats[name].concept.strip():
            SiteCategory.objects.filter(pk=cats[name].pk).update(concept=concept)
    for head, name in MOVES.items():
        if name not in cats:
            continue
        for pl in Placement.objects.filter(site_category__blog__name="black_lukey", deleted_at__isnull=True):
            post = pl.naver_post or pl.tistory_post
            if post is not None and post.title.startswith(head) and pl.site_category_id != cats[name].pk:
                Placement.objects.filter(pk=pl.pk).update(site_category=cats[name])


def backward(apps, schema_editor):
    SiteTemplate = apps.get_model("site_templates", "SiteTemplate")
    SiteCategory = apps.get_model("blog_types", "SiteCategory")
    SiteTemplate.objects.filter(blog__name="black_lukey", **NEW).update(**OLD)
    for name, concept in CONCEPTS.items():
        SiteCategory.objects.filter(blog__name="black_lukey", name=name, concept=concept).update(concept="")


class Migration(migrations.Migration):
    dependencies = [("site_templates", "0007_tidy_templates"), ("blog_types", "0019_nunip_site_categories")]
    operations = [migrations.RunPython(forward, backward)]
