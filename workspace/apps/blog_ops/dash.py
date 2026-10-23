"""모니터링 대시보드 (2026-10-23 사용자: 숫자 칸 줄은 빼고, 역할이 분명한 네 칸을 좌우 5:5 로 큼지막하게).

- 왼쪽 위 발행 실적: 사이트 × 요일 한 주 (views.index). 칸을 누르면 왼쪽 아래가 그날 · 그 사이트로 바뀐다.
- 오른쪽 위 일일루틴 글쓰기: 실행 버튼 + 오늘 실행 상태 + 글쓰기 결과 (분류마다 씀·예정·못 씀·없음, routines.results).
  결과 줄마다 '실행' — 그 소재(또는 매일 고정 주제) 1편만 (커스텀 글쓰기의 한 줄 실행, routines.topics.run).
- 왼쪽 아래 발행: 그날 발행 예정인 글(발행예정글, 예정일 = 그날)과 발행한 글을 사이트별로. 줄마다 변환 · 발행 완료.
  오늘이면 오늘 만든 발행예정글 중 예정일을 안 정한 것도 (오늘의 글에서 옮긴 글, 2026-10-23 사용자).
- 오른쪽 아래 오늘의 글: 오늘 만든 글을 사이트별로. 줄마다 '발행예정으로' (임시·검토에서 한 번에, posts.promote).

글의 사이트는 글 관리와 같다 (posts.site_of: 고른 사이트, 없으면 넣은 곳의 사이트).
"""
from django.conf import settings
from django.db.models import Prefetch
from django.utils import timezone

from .feeds import _norm

STAGE_LABELS = {"temp": "임시", "review": "검토", "post": "발행예정"}


def _posts(**filters):
    """두 글 표에서 조건에 맞는 글 (넣은 곳을 미리 읽고, writer · ref 를 붙인다)."""
    from apps.blog_types.classify import WRITERS, post_model
    from apps.blog_types.models import Placement
    out = []
    pls = Prefetch("placements", queryset=Placement.objects.select_related("site_category__blog"))
    for w in WRITERS:
        for post in post_model(w).objects.filter(**filters).prefetch_related(pls).order_by("created_at", "pk"):
            post.writer, post.ref = w, f"{w}:{post.pk}"
            out.append(post)
    return out


def _by_site(rows, blogs, key):
    """[(사이트 이름, [줄])] — 운영 화면 사이트 순서, 사이트를 안 정한 글은 끝."""
    order = [b.name for b in blogs]
    groups = {}
    for row in rows:
        groups.setdefault(key(row) or "사이트 미정", []).append(row)
    names = sorted(groups, key=lambda n: order.index(n) if n in order else len(order))
    return [(n, groups[n]) for n in names]


def day_posts(blogs, day, done, site=None):
    """그날 발행 예정 · 발행한 글을 사이트별로. done = views.published 의 그 주 결과 (RSS 로만 읽힌 글도 보인다).
    줄: {post (없으면 None), title, url, state: planned|done, placement}"""
    from apps.blog_types.posts import site_of
    names = {b.name for b in blogs if site in (None, b.pk)}
    rows, seen = [], set()
    undated = _posts(stage="post", planned_on=None, created_at__date=day) if day == timezone.localdate() else []
    planned = _posts(stage="post", planned_on=day) + undated
    _place_defaults(planned)
    for post in planned + _posts(publish_status="done", published_on=day):
        if (post.writer, post.pk) in seen or site_of(post) not in names:
            continue
        seen.add((post.writer, post.pk))
        state = "done" if post.publish_status == post.Publish.DONE else "planned"
        pl = next(iter(post.placements.all()), None)
        rows.append({"post": post, "title": post.title, "url": "", "state": state, "placement": pl, "site": site_of(post)})
    # 글 관리에 있는 글은 RSS 줄을 또 넣지 않는다. 블로그에는 변환 제목으로 올라가니 그것도 견준다
    # (2026-10-23 사용자: 밤밤 코스피 글이 원문 제목 · 변환 제목으로 두 줄 떴다)
    titles = {_norm(t) for r in rows if r["post"] for t in
              [r["post"].title, *(pl.converted_title for pl in r["post"].placements.all())] if t}
    for b in blogs:  # RSS 로만 읽힌 그날 글 (글 관리에 없는 글)
        if b.name in names:
            for title, url in done.get((b.pk, day), {}).values():
                if _norm(title) not in titles:
                    rows.append({"post": None, "title": title, "url": url, "state": "done", "placement": None, "site": b.name})
    rows.sort(key=lambda r: r["state"] != "planned")  # 예정이 위
    return _by_site(rows, blogs, lambda r: r["site"])


def _place_defaults(posts):
    """카테고리가 빈 예정 글은 원고의 '넣을 카테고리'로 넣어 둔다 (2026-10-23 사용자: 모니터링에서 변환을 누르면
    카테고리가 이미 정해진 글은 고르는 화면 없이 바로 변환). 넣은 글은 placements 를 다시 읽는다."""
    from apps.blog_types import sites
    empty = [p for p in posts if not p.placements.all()]
    if empty and sites.place_defaults(empty):
        for p in empty:
            p._prefetched_objects_cache.pop("placements", None)


def ready_ids(groups):
    """'전체 변환'에 넣을 매핑 번호: 그날 예정 글 중 카테고리에 넣었고 아직 변환 안 한 것."""
    return [x["placement"].pk for _, items in groups for x in items
            if x["state"] == "planned" and x["placement"] and x["placement"].convert_status == "none"]


def new_posts(blogs, day):
    """그날 만든 글을 사이트별로 (오늘의 글). 줄: post (.stage_label)"""
    from apps.blog_types.posts import site_of
    posts = _posts(created_at__date=day)
    for p in posts:
        p.stage_label = "발행 완료" if p.publish_status == p.Publish.DONE else STAGE_LABELS.get(p.stage, p.stage)
    return _by_site(posts, blogs, site_of)


def writing(request, day):
    """일일루틴 글쓰기: 실행 안내문 · 오늘 실행 · 글쓰기 결과. 루틴이 없으면 None."""
    from apps.routines.models import Routine
    from apps.routines.results import counts, writing_results
    from apps.routines.views import launcher, report_url
    routine = Routine.objects.filter(key="writing").first()
    if routine is None:
        return None
    from apps.routines.models import FixedTopic
    rows = writing_results(day)
    daily = {f"{t.site or '사이트 미정'} > {t.name}": f"f{t.pk}" for t in FixedTopic.objects.filter(daily=True, category=None)}
    for r in rows:  # 줄마다 실행 (2026-10-23 사용자: 코스피는 시간을 보고 따로 돌린다)
        r["run"] = r["sel"] or daily.get(r["label"], "")
    return {"routine": routine, "prompt": launcher(routine, day, report=report_url(request, routine, day)),
            "run": routine.runs.filter(day=day).first(), "results": rows, "counts": counts(rows),
            "on_server": settings.IS_SERVER}
