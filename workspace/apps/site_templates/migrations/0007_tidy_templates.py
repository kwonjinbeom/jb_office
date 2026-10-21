"""2026-10-21 사용자: 변환본이 원문보다 못하다 — 사이트 템플릿·붙여넣기 포맷에 쓸데없는 것이 많아 변환이 원문을 다시 짜며
지저분해졌다. 공통 규칙(prompt.KEEP · FACT_CHECK · PHOTOS)과 겹치거나, 붙인 뒤 사람이 할 일이거나, 원문을 다시 짜게 만드는 줄을 뺀다.
처음 넣은 값(0002~0006 을 거친 값) 그대로일 때만 바꾼다. 화면에서 고친 값은 그대로 둔다."""
from importlib import import_module

from django.db import migrations


def _old_formats():
    seed = import_module("apps.site_templates.migrations.0003_paste_research").NEW
    old = dict(seed)
    for platform, (a, b) in import_module("apps.site_templates.migrations.0004_find_photos").CHANGE.items():
        old[platform] = old[platform].replace(a, b)
    for name in ("0005_naver_photos", "0006_naver_photos_paste"):
        mod = import_module(f"apps.site_templates.migrations.{name}")
        old["naver"] = old["naver"].replace(mod.OLD, mod.NEW)
    return old


FORMATS = {
    "naver": "\n".join([
        "서식 그대로 붙인다 (HTML 모드 없음). 표는 칸 합치기 없이 단순하게.",
        "코드 블록은 쓰지 않는다 (한 줄로 뭉개진다).",
        "본문에 #단어 를 쓰지 않는다 (태그로 등록된다). 태그는 30개 이하, 띄어쓰기 없이.",
        "제목 100자 이하, 제목에는 이모지 없이.",
    ]),
    "tistory": "\n".join([
        "HTML 로 붙인다. 소제목은 ## · ### · #### 만 (# 은 글 제목 자리).",
        "글자색·크기·글꼴 꾸밈 없이 굵게·밑줄·목록·인용·표(칸 합치기 없이)·코드만.",
        "링크 카드·유튜브는 주소만 한 줄로.",
        "접은글은 [접은글 시작] / [접은글 끝] 표시만.",
    ]),
    "blogger": "\n".join([
        "HTML 보기에 붙인다. 소제목은 ## (h2) 부터.",
        "문단·굵게·기울임·목록·인용·표·코드·링크만. 글자색·크기 꾸밈 없이.",
        "목록에서 '더 읽기'로 끊을 자리는 <!-- more --> 한 줄.",
        "라벨은 글당 20개·합계 200자 이하. 제목은 60자 안쪽.",
    ]),
    "wordpress": "\n".join([
        "블록 에디터에 마크다운 그대로 붙인다. 소제목은 ## 부터.",
        "글자색·크기·정렬·밑줄은 지워진다 → 굵게·기울임·인용으로만 강조.",
        "문단 안에서 줄을 바꾸지 않는다. 문단 사이는 빈 줄.",
        "사진은 넣지 않는다 (미디어 라이브러리에 직접 올린다). 접은 글(details)은 쓰지 않는다.",
    ]),
}

# 사이트마다 그 사이트에만 필요한 것. 구성(소제목 틀)은 원문을 다시 짜게 만들어 정보성 사이트에서 뺀다.
TEMPLATES = {
    "눈잎": dict(tone="정보성 해요체, 짧은 문단.", structure="", rules=""),
    "밤밤": dict(tone="정보성 해요체, 눈잎보다 간결하게.", structure="", rules="눈잎과 주제·내용이 겹치지 않게."),
    "black_lukey": dict(tone="소개·정보 해요체, 짧은 문단, 가벼운 이모티콘 조금.", structure="",
                        rules="쇼핑커넥트 링크는 참여 스마트스토어 상품만, 대가 문구는 첫 부분."),
}


def forward(apps, schema_editor):
    PlatformFormat = apps.get_model("site_templates", "PlatformFormat")
    SiteTemplate = apps.get_model("site_templates", "SiteTemplate")
    old = _old_formats()
    for platform, guide in FORMATS.items():
        PlatformFormat.objects.filter(platform=platform, guide=old[platform]).update(guide=guide)
    seed = import_module("apps.site_templates.migrations.0002_seed").TEMPLATES
    for name, new in TEMPLATES.items():
        SiteTemplate.objects.filter(blog__name=name, **seed[name]).update(**new)


def backward(apps, schema_editor):
    PlatformFormat = apps.get_model("site_templates", "PlatformFormat")
    SiteTemplate = apps.get_model("site_templates", "SiteTemplate")
    old = _old_formats()
    for platform, guide in FORMATS.items():
        PlatformFormat.objects.filter(platform=platform, guide=guide).update(guide=old[platform])
    seed = import_module("apps.site_templates.migrations.0002_seed").TEMPLATES
    for name, new in TEMPLATES.items():
        SiteTemplate.objects.filter(blog__name=name, **new).update(**seed[name])


class Migration(migrations.Migration):
    dependencies = [("site_templates", "0006_naver_photos_paste")]
    operations = [migrations.RunPython(forward, backward)]
