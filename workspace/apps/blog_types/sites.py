"""사이트 고르기와 발행 상태 맞추기 (글 관리 · 글 보기 · 카테고리 관리 · 사이트별 템플릿 공용).

- 글의 '사이트'(Post.target)는 운영 화면의 블로그 이름 하나. 원고의 `사이트:` 줄로 들어오고, 검토글·발행예정글에서 고른다.
- 발행 상태: 글(Post.publish_status)과 그 글을 넣은 곳(Placement.status)을 같이 움직인다 (2026-10-17 사용자:
  사용자가 직접 발행하고 발행 완료로 바꾼다). 글을 바꾸면 넣은 곳 모두, 넣은 곳을 바꾸면 모두 발행 완료일 때만 글도 발행 완료.
"""
import re

from django.utils import timezone

from apps.blog_rules.models import Blog

from .models import Placement


def names():
    """사이트 이름 (운영 화면 순서)"""
    return list(Blog.objects.order_by("order", "pk").values_list("name", flat=True))


def _set_post(post, done):
    model = type(post)
    value = model.Publish.DONE if done else model.Publish.TODO
    fields = []
    if post.publish_status != value:
        post.publish_status = value
        fields.append("publish_status")
    if done and not post.published_on:
        post.published_on = timezone.localdate()
        fields.append("published_on")
    if fields:
        post.save(update_fields=[*fields, "updated_at"])
    return bool(fields)


def publish(post, done):
    """글의 발행 상태를 바꾸고, 그 글을 넣은 곳(매핑)도 같은 상태로."""
    _set_post(post, done)
    status = Placement.Status.PUBLISHED if done else Placement.Status.UNSAVED
    post.placements.exclude(status=status).update(status=status, updated_at=timezone.now())


def _bare(name):
    return re.sub(r"\s+", "", name or "")


def _site_category(place):
    """'사이트 › 카테고리(› 하위)' → 그 사이트 카테고리 (띄어쓰기만 달라도 같은 것). 없으면 None."""
    from .models import SiteCategory
    parts = [p.strip() for p in re.split(r"[›>]", place) if p.strip()]
    if len(parts) < 2:
        return None
    cats = list(SiteCategory.objects.filter(blog__name=parts[0]).select_related("parent"))
    want = [_bare(p) for p in parts[1:]]
    for c in cats:  # 하위까지 적었으면 상위 › 하위, 아니면 맨 위 카테고리 먼저
        path = [_bare(c.parent.name), _bare(c.name)] if c.parent_id else [_bare(c.name)]
        if path == want:
            return c
    return next((c for c in cats if _bare(c.name) == want[-1]), None)


# 고정 주제마다 정해 둔 넣을 곳 (원고의 '넣을 카테고리'보다 먼저). 2026-10-23 사용자: AI 소식은 memorily › AI 로.
TOPIC_PLACES = {"AI 소식": "memorily › AI"}


def place_defaults(posts):
    """발행예정글로 온 글에 넣은 곳이 한 번도 없으면 원고의 '넣을 카테고리'(처음 겨냥한 사이트 › 카테고리)에 넣는다.
    2026-10-23 사용자: 담으면 카테고리가 비어 있었다 — 거의 처음 겨냥이 맞고, 바꾸는 건 사용자가 한다.
    지웠던 적이 있는 글(휴지통의 넣은 곳)은 다시 넣지 않는다. 넣은 수를 돌려준다."""
    from apps.routines.views import naver_drafts_dir
    from apps.writing import drafts as drafts_mod

    posts = [p for p in posts if not Placement.all_objects.filter(**{_field(p): p}).exists()]
    if not posts:
        return 0
    by_title = {}
    for folder in (drafts_mod.drafts_dir(), naver_drafts_dir()):
        for d in drafts_mod.list_drafts(folder):
            place = TOPIC_PLACES.get(d.topic) or d.place
            if place:
                by_title.setdefault(d.title, place)
    added = 0
    for post in posts:
        cat = _site_category(by_title.get(post.title, ""))
        if cat is not None:
            Placement.objects.create(site_category=cat, **{_field(post): post})
            added += 1
    return added


def _field(post):
    return "naver_post" if post._meta.app_label == "naver_writing" else "tistory_post"


def sync_post(post):
    """넣은 곳의 발행 상태가 바뀐 뒤: 모두 발행 완료면 글도 발행 완료, 하나라도 미발행이면 글은 미발행."""
    statuses = list(post.placements.values_list("status", flat=True))
    if statuses:
        _set_post(post, all(s == Placement.Status.PUBLISHED for s in statuses))
