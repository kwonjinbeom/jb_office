"""memorily 총정리 제목 (2026-10-31 사용자: "AI 소식 말고 나머지는 총정리 컨셉이다. 컨셉 이름을 제목에 고정하고 상세를 덧붙여야지").

무료 AI 툴 · 이달의 AI · IT 할인 글의 제목 = `<시리즈 이름> · <이번 편> — <상세 한 줄>`. 시리즈 이름은 매번 그대로.
고정 주제 지침(작가가 받는 것)과 사이트 카테고리 갈래 컨셉(변환이 받는 것)에 같은 줄을 더한다. 이미 있으면 건너뛴다.
같은 글이 작가 파일(일일루틴/프롬프트/writing_site_memorily.md)에도 있다 — 고칠 때 둘 다. 지우는 데이터 없음.
"""
from django.db import migrations

MARK = "제목 (2026-10-31 사용자, 총정리 이름 고정)"
# 주제 → (시리즈 이름, 이번 편, 예)
SERIES = {
    "무료 AI 툴": ("무료 AI 툴 총정리", "용도 (PPT · 영상 · 이미지 …)",
               "무료 AI 툴 총정리 · PPT — Gamma·Canva·Presenton 무료로 어디까지 (10월 31일 기준)"),
    "이달의 AI": ("이달의 AI 총정리", "그달 (2026년 10월)",
              "이달의 AI 총정리 · 2026년 10월 — ChatGPT 사용 한도 2배, Gemini 4 Carbon 공개"),
    "IT 할인": ("IT 할인 총정리", "행사 (광군제 · 블랙프라이데이 …)",
              "IT 할인 총정리 · 광군제·블랙프라이데이 2026 — 날짜와 살 만한 것"),
}


def line(name):
    series, part, example = SERIES[name]
    return (f"{MARK}: `{series} · <{part}> — <상세 한 줄>`. 앞의 '{series}'는 매번 글자 그대로 두고, "
            f"이번 편과 상세(검색어 · 숫자 · 기준일)만 바꾼다. 예) `{example}`")


def forward(apps, schema_editor):
    FixedTopic = apps.get_model("routines", "FixedTopic")
    SiteCategory = apps.get_model("blog_types", "SiteCategory")
    for name in SERIES:
        for topic in FixedTopic.objects.filter(name=name, deleted_at__isnull=True):
            if MARK not in topic.note:
                topic.note = (topic.note.rstrip() + "\n- " + line(name)).strip()
                topic.save(update_fields=["note"])
        for cat in SiteCategory.objects.filter(blog__name="memorily", name=name, deleted_at__isnull=True):
            if MARK not in cat.concept:
                cat.concept = (cat.concept.rstrip() + "\n\n" + line(name)).strip()
                cat.save(update_fields=["concept"])


class Migration(migrations.Migration):
    dependencies = [("routines", "0023_memorily_topics"), ("blog_types", "0054_memorily_branches")]
    operations = [migrations.RunPython(forward, migrations.RunPython.noop)]
