"""처음 값 (2026-10-16): 운영 화면의 컨셉·체크와 포스팅자동화 03·07·10·12 문서에서 옮겼다. 화면에서 고치는 것이 원본.
이미 있으면 넣지 않는다."""
from django.db import migrations

FORMATS = {
    "tistory": "\n".join([
        "기본모드 에디터에 '서식 그대로' 붙여넣기, 또는 HTML 모드에 HTML 붙여넣기.",
        "소제목은 h2·h3. 표·인용·구분선은 인라인 스타일이 붙은 채로.",
        "이미지는 직접 업로드 (외부 주소 이미지는 쓰지 않는다). 대체 텍스트를 단다.",
        "답·긴 표는 에디터의 접은글(더보기)로.",
        "제휴 링크가 있으면 제목 아래 첫 줄에 대가 문구. 본문 광고는 2~3개 안쪽이라 문단 사이를 너무 촘촘히 두지 않는다.",
        "태그는 쉼표로.",
    ]),
    "naver": "\n".join([
        "스마트에디터 ONE 본문에 '서식 그대로' 붙여넣기 (글꼴·크기는 도구가 붙여 준다).",
        "붙인 뒤 소제목·표가 남았는지 한 번 확인한다.",
        "사진은 직접 올리고, 사진 하나에 짧은 문단 하나씩 리듬을 맞춘다.",
        "쇼핑커넥트 링크가 있으면 대가 문구를 첫 부분에. AI 생성 이미지를 쓰면 'AI 활용' 표시를 켠다.",
        "태그는 # 해시태그.",
    ]),
    "wordpress": "\n".join([
        "블록 에디터에 붙여넣으면 블록으로 나뉜다 (또는 '사용자 지정 HTML' 블록).",
        "이미지는 미디어 라이브러리에 올린다. 카테고리·태그·요약(발췌) 칸을 채운다.",
        "요금제·설치형은 사용자와 마지막에 정한다.",
    ]),
    "blogger": "\n".join([
        "글쓰기 화면의 'HTML 보기'에 HTML 붙여넣기.",
        "이미지는 직접 올리거나 외부 주소. 라벨(카테고리)과 검색 설명을 채운다.",
    ]),
}

TEMPLATES = {
    "memorily": dict(
        tone="개발자 1인칭. AI를 쓰며 겪은 것·느낀 점을 내 방식으로, 과장 없이 담백하게.",
        structure="겪은 상황 → 해 본 것(코드·화면) → 결과와 느낀 점 → 다음에 해 볼 것",
        rules="직접 해 본 것만 쓴다. 코드·에러 메시지는 실제 것.",
    ),
    "눈잎": dict(
        tone="정보성: 해요체, 짧은 문단, 숫자마다 판단 한 줄.",
        structure="결론 먼저 → 표·달력 → 조건별 판단(이런 사람은 이것) → 확인일·출처",
        rules="숫자·날짜는 원 출처에서 한 번 더. 안 나온 일정은 '미정'. 가장 공들인 정보성 원고는 여기.",
    ),
    "밤밤": dict(
        tone="정보성: 눈잎과 같은 결, 더 간결하게.",
        structure="결론 먼저 → 표 → 판단 한 줄 → 출처",
        rules="눈잎과 주제·내용이 겹치지 않게.",
    ),
    "black_lukey": dict(
        tone="소개·정보: 사진 리듬에 맞춘 짧은 문단, 가벼운 이모티콘 조금.",
        structure="사진 → 한두 줄 설명을 반복, 마지막에 누구에게 맞는지",
        rules="쇼핑커넥트 링크는 참여 스마트스토어 상품만, 대가 문구는 첫 부분. 숫자·날짜는 원 출처에서 한 번 더.",
    ),
}


def seed(apps, schema_editor):
    PlatformFormat = apps.get_model("site_templates", "PlatformFormat")
    SiteTemplate = apps.get_model("site_templates", "SiteTemplate")
    Blog = apps.get_model("blog_rules", "Blog")
    for platform, guide in FORMATS.items():
        PlatformFormat.objects.get_or_create(platform=platform, defaults={"guide": guide})
    for blog in Blog.objects.filter(deleted_at__isnull=True):
        SiteTemplate.objects.get_or_create(blog=blog, defaults=TEMPLATES.get(blog.name, {}))


class Migration(migrations.Migration):
    dependencies = [("site_templates", "0001_initial"), ("blog_rules", "0007_checks_by_site")]
    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
