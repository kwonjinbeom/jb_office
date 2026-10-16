"""프롬프트를 저장소 md 로 (2026-10-16 사용자: 로컬·클라우드는 같은 프롬프트를 보고, 클라우드 제약은 md 하나로).

루틴마다 prompt_doc(일일루틴/프롬프트/<키>.md)·오늘의 자료·갱신 때 볼 관점을 채운다. 비어 있을 때만.
예전 DB 프롬프트(prompt_local·prompt_cloud)는 지우지 않고 남겨 둔다.
"""
from django.db import migrations

SETUP = {
    "daily_ideas": ("일일루틴/프롬프트/daily_ideas.md", "existing,standard",
                    "후보가 실제 수요 신호(검색·커뮤니티·판매)로 뒷받침되는지, 지난 후보와 겹치지 않는지, "
                    "작게 만들어 첫 반응을 볼 수 있는지, 출처가 확인 가능한지."),
    "tistory": ("일일루틴/프롬프트/tistory.md", "sites,existing",
                "AI 글쓰기 유의점: 숫자·날짜·정책은 원 출처 확인, 같은 주제·제목 반복 금지, 사이트 컨셉과 체크 지키기, "
                "검색 의도에 맞는 제목·첫 문단, 애드센스·저작권 정책 위반 없는지, 기계적인 문체·과장 피하기."),
    "naver": ("일일루틴/프롬프트/naver.md", "sites,existing",
              "AI 글쓰기 유의점: 네이버 검색(방문자) 관점의 제목·구성, 숫자·날짜는 원 출처 확인, 같은 주제 반복 금지, "
              "쇼핑커넥트 링크 규칙(참여 상품만)과 광고 표기, 저품질로 보일 반복·과장 문체 피하기."),
}


def forward(apps, schema_editor):
    Routine = apps.get_model("routines", "Routine")
    for key, (doc, data, focus) in SETUP.items():
        r = Routine.objects.filter(key=key).first()
        if r is None:
            continue
        r.prompt_doc = r.prompt_doc or doc
        r.data = r.data or data
        r.review_focus = r.review_focus or focus
        r.save(update_fields=["prompt_doc", "data", "review_focus"])


class Migration(migrations.Migration):
    dependencies = [("routines", "0004_prompt_md_eval")]
    operations = [migrations.RunPython(forward, migrations.RunPython.noop)]
