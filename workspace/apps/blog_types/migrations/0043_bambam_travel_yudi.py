"""밤밤 › 해외여행을 눈잎 › 일본 여행과 같은 컨셉으로 (2026-10-28 사용자: "밤밤 해외여행이 다른 카테고리들처럼 딱딱하다 —
유연한 눈잎으로 맞추려고"). 앞으로 쓰고 변환하는 글부터 적용된다 (이미 올린 글은 그대로 둔다).

1. 카테고리 컨셉: 계산형(경비표·패스 손익 나열) → 일본 여행의 짜임새(권역·도시, 일정 표, 공항 교통, 패스 계산, 일차별 사진·메모, 준비 체크리스트)를
   일본 밖 나라·도시에 맞게. 위치 지도 줄은 그대로 남긴다.
2. 글 모양(look) → 유디 메모지 (가운데 정렬·메모지 상자·둥근 소제목). 블로거는 붙여 넣는 HTML 이 글꼴도 함께 불러온다 (site_templates.views).
3. 밤밤 사이트 컨셉 문구의 '해외여행(경비·패스 계산형)'.
지우는 데이터 없음. 되돌리면 예전 컨셉·모양으로.
"""
import re

from django.db import migrations

CONCEPT = """해외 나라·도시 한 곳을 눈잎 › 일본 여행과 같은 짜임·화면으로 소개한다 (2026-10-28 사용자: 계산형은 딱딱하다 → 유연한 눈잎처럼). 일본은 눈잎 › 일본 여행이 쓴다 — 여기는 일본 밖만. 한 편에 한 도시 또는 한 권역(거점 도시 + 묶어 다녀오는 곳). 같은 나라·도시는 14일 안에 다시 쓰지 않는다.
무엇을 쓸지:
- 그때의 신호로 고른다: 한국인 검색·예약이 느는 곳, 새 직항·특가, 2~4주 뒤 시즌(축제·단풍·눈·크리스마스 마켓·건기).
- 글 종류를 돌린다: ① 도시·권역 N박 N일 코스 ② 한 도시·한 지역 집중 (근교 당일치기 포함) ③ 준비·교통 (공항 → 시내, 패스·교통카드, 환전·결제) ④ 입국 제도·항공·환율 소식.
- 일정 길이·거점·동선은 그곳의 거리와 교통에 맞춰 새로 짠다. 지난 글의 일수·거점·순서를 옮겨 오지 않는다.
짜임새 (동선·교통·시간·돈이 한눈에 맞아떨어져야 한다):
- 글 종류에 맞는 것만 쓴다. 코스 글은 아래 전부. 도시 집중은 일정 표·공항 교통을 줄이고 장소를 깊게. 준비·교통 글은 비교표·계산이 본문. 소식 글은 결론 → 바뀐 것 → 나에게 미치는 영향.
- 길이: 줄이지 않는다. 문단은 짧게, 정보는 표·메모지 상자로.
- 순서 (코스 글): 맨 위 인용(누구에게 · 며칠 · 핵심 동선 한 줄) → 위치 지도 → 목차 → 한눈에 보는 일정 표 → 공항에서 시내 → 교통(패스·교통카드 또는 렌터카) → 숙소 거점 → 일차별 → 여행 전 준비 → 마무리.
- 한눈에 보는 일정 표: 일차 · 거점 · 동선(A → B → C) · 이동 수단·시간 · 그날 교통비(현지 통화 + 원). 첫 화면에서 여행 전체가 보이게.
- 공항에서 시내: 그 도시 공항(둘이면 둘 다)에서 거점까지 갈 수 있는 수단을 모두 — 도착역 · 소요 시간 · 편도 요금 · 장점 · 맞는 사람 비교표.
- 교통: 그 일정에 패스·교통카드가 이득인지 계산한다 (패스 값 vs 구간별 낱개 합, 구간·요금 표). 포함·불포함과 실전 주의. 이득이 아니면 '안 사도 된다'고 쓴다. 렌터카가 나은 곳은 렌터카·주차·통행료.
- 숙소 거점: 특정 호텔이 아니라 그 동선에 유리한 역·동네와 이유 한두 줄.
- 일차별: `## N일차 · 그날 지역` → 그날 동선 한 줄 → 이동(노선 이름 · 탈 역 · 내릴 역 · 출구 · 도보 몇 분 · 요금) → 갈 곳마다: ① 사진 1장 이상 (그 장소가 실제로 찍힌 사진, 가로 우선, 2장이면 콜라주). ② 서술 2~4문장: 어떤 곳인지 · 무엇을 보는지 · 몇 시에 가면 덜 붐비는지 · 다음 장소로 가는 길. ③ 정보 카드 `::: 장소 | 정식 이름(현지 표기)` — ⏰ 운영 시간 · 🚪 입장 마감 · 💳 입장료(현지 통화 + 원) · 📅 휴무 · 🎫 예약(공식·예매처 링크) · 🚇 가는 법(역·출구·도보) · 📍 지도(구글 지도 링크 `https://www.google.com/maps/search/?api=1&query=<이름>`). 무료·상시 개방도 카드를 넣는다. ④ 맛집·카페는 동선 위의 유명한 곳만 1~3곳: 1~2문장 + `::: 맛집 | 이름` (🍽️ 대표 메뉴·가격 현지 통화 + 원 · ⏰ 영업·휴무 · 💡 줄·예약 팁 · 📍 구글 지도).
- 돈: 금액은 현지 통화 + 원을 같이 쓰고, 일정 표 아래에 기준 환율 한 줄 (쓰는 날의 은행 고시 환율과 날짜).
- 여행 전 준비 (코스·준비 글): 입국(비자·전자여행허가·입국 신고 — 확인한 날짜와 함께) · eSIM·로밍 · 결제(교통카드·트래블 카드·현금이 필요한 곳) · 그 시기 날씨·옷차림 · 팁·세금 환급 — 체크리스트 한 묶음.
- 시리즈: 한 나라를 나눠 쓰면 글 끝에 앞뒤 편을 잇는다.
- 말투: 사이트의 담백한 해요체를 지키되 눈잎 일본 여행처럼 짧게 끊어 부드럽게. 숫자는 정확하게.
- 하지 않는 것: 'TOP 10'·'가볼만한곳 BEST' 나열, 가 본 척("먹어 보니", "다녀왔는데"), 근거 없는 시간·가격, 링크 자리만 남기기. 다녀온 사람들의 후기는 '다녀온 사람들은 …'으로 쓰고 출처를 단다.
- 마무리: 표·목록 없이 서술 2~4문장 — 이 일정의 어느 날 무엇을 즐기면 좋은지, 잘 다녀오라는 인사. '도움이 되셨길' 같은 상투어 금지.
{locator}
화면 모양 (유디 블로그의 화면 짜임, 붙여 넣는 HTML 이 그린다 — 변환본에는 꾸밈 코드를 넣지 않는다):
- 가운데 정렬, 한 줄에 한 호흡 (짧게 끊어 줄바꿈, 2~4줄이 한 단락, 단락 사이 넉넉히).
- 나눔스퀘어 본문, 굵게는 청록 굵은 글자 · 가장 중요한 한 구절은 연두 형광펜(==…==).
- 소제목은 코랄 큰따옴표 + 둥근 굵은 글씨 + 연두 형광펜 밑칠 (소제목 말은 위 짜임새대로 — 일차는 `## N일차 · 그날 지역`), 큰 단락 사이 가운데 나눔표(---).
- 정보는 모서리 접힌 메모지 상자(청록 글자) · 목차는 가운데 좁은 표(머리 칸 연두) · 맨 위 인용은 연한 청록 둥근 상자 · 사진은 2장씩 콜라주, 둥근 모서리. 위치 지도는 자르지 않고 한 장 그대로."""

LOCATOR = ("- 위치 지도 (2026-10-27 사용자: 어디인지 감이 안 온다): 맨 위 인용 바로 다음(인용 아래 대표 사진이 있으면 그 다음)에 1장, "
           "변환이 그린다 (변환그림/위치지도.py 밤밤). 모양: 제목 '<나라> <도시>' + '<대륙> · 서울에서 직선 약 N km' 한 줄, "
           "두 칸 — 왼쪽 서울에서 그 도시까지 점선, 오른쪽 그 나라를 빨강으로 칠하고 독자가 아는 이웃 도시 3~5곳. "
           "흰 바탕·회색 땅·빨강 한 가지, 출처 'Natural Earth'. 캡션 줄 없음, 대표 사진으로 쓰지 않는다.")
SITE = ("해외여행(경비·패스 계산형)", "해외여행(나라·도시 코스 — 눈잎 일본 여행 짜임)")
MARK = "눈잎 › 일본 여행과 같은 짜임·화면"


def _locator(concept):
    """지금 컨셉의 위치 지도 줄 (사용자가 고쳤으면 고친 그대로)"""
    m = re.search(r"^- 위치 지도 \(.*$", concept or "", re.M)
    return m.group(0) if m else LOCATOR


def forward(apps, schema_editor):
    SiteCategory = apps.get_model("blog_types", "SiteCategory")
    Section = apps.get_model("blog_types", "Section")
    Blog = apps.get_model("blog_rules", "Blog")
    for cat in SiteCategory.objects.filter(blog__name="밤밤", name="해외여행", deleted_at__isnull=True):
        if MARK in cat.concept:
            continue
        cat.concept = CONCEPT.format(locator=_locator(cat.concept))
        cat.look = "yudi"
        cat.save(update_fields=["concept", "look"])
    for blog in Blog.objects.filter(name="밤밤", deleted_at__isnull=True):
        if SITE[0] in blog.content:
            blog.content = blog.content.replace(*SITE)
            blog.save(update_fields=["content"])
    for sec in Section.objects.filter(name="밤밤", deleted_at__isnull=True):
        if SITE[0] in sec.note:
            sec.note = sec.note.replace(*SITE)
            sec.save(update_fields=["note"])


OLD = ("해외 나라·도시 한 곳을 숫자로 소개한다 (계산형). 일본은 눈잎 › 일본 여행이 쓴다 — 여기는 일본 밖만. 같은 나라·도시는 14일 안에 다시 쓰지 않는다.\n"
       "- 'TOP 10'·'가볼만한곳 BEST' 나열 대신: 일정별 경비표 · 교통 패스 손익 · 공항에서 시내 비교 · 그 시기에만 되는 것(날짜) · 확인일이 붙은 입국 조건·환율.\n"
       "- 경험·감상 없이 담백하게. 갈 곳 정보는 정보 카드로 짧게 (📍 는 구글 지도 링크 `https://www.google.com/maps/search/?api=1&query=<이름>`).\n")


def backward(apps, schema_editor):
    SiteCategory = apps.get_model("blog_types", "SiteCategory")
    Section = apps.get_model("blog_types", "Section")
    Blog = apps.get_model("blog_rules", "Blog")
    for cat in SiteCategory.objects.filter(blog__name="밤밤", name="해외여행", deleted_at__isnull=True):
        if MARK in cat.concept:
            cat.concept = OLD + _locator(cat.concept)
            cat.look = ""
            cat.save(update_fields=["concept", "look"])
    for model, field in ((Blog, "content"), (Section, "note")):
        for obj in model.objects.filter(name="밤밤", deleted_at__isnull=True):
            if SITE[1] in getattr(obj, field):
                setattr(obj, field, getattr(obj, field).replace(SITE[1], SITE[0]))
                obj.save(update_fields=[field])


class Migration(migrations.Migration):
    dependencies = [("blog_types", "0042_cleanup_empty"), ("blog_rules", "0009_site_targets")]
    operations = [migrations.RunPython(forward, backward)]
