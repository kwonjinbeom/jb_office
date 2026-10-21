"""티스토리 글쓰기 ↔ 네이버 글쓰기 보내기 (2026-10-16 사용자).

원래 글은 그대로 두고, 상대 글쓰기의 **임시글**에 복사본을 만든다. 같은 원고를 두 플랫폼에 맞게 고쳐 쓰기 위해서다.
제목·요약·태그·본문·글 분류·타겟을 옮긴다. 분류가 상대 플랫폼에 없는 카테고리면(예: 네이버 전용 G 여행·체험) 미분류로 둔다.
본문은 상대 글쓰기의 HTML 규칙으로 한 번 더 거른다 (마크다운은 그대로).
"""
from django.db import transaction

from . import classify

OTHER = {"tistory": "naver", "naver": "tistory"}


def _render(writer):
    if writer == "naver":
        from apps.naver_writing import render
    else:
        from apps.writing import render
    return render


@transaction.atomic
def send(post):
    dst = OTHER[classify.writer_of(post)]
    Target = classify.post_model(dst)
    render = _render(dst)
    body = post.body or ""
    if render.is_html(body):
        body = render.clean_html(body)
    copy = Target(stage=Target.Stage.TEMP, title=post.title, summary=post.summary, tags=post.tags, body=body,
                  target=post.target)
    node = classify.node_of(post)
    if node is not None and classify.categories_for(dst).filter(pk=post.bt_category_id).exists():
        classify.assign(copy, node.sel)
    copy.save()
    return copy
