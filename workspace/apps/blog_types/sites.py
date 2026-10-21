"""사이트 고르기와 발행 상태 맞추기 (글 관리 · 글 보기 · 카테고리 관리 · 사이트별 템플릿 공용).

- 글의 '사이트'(Post.target)는 운영 화면의 블로그 이름 하나. 원고의 `사이트:` 줄로 들어오고, 검토글·발행예정글에서 고른다.
- 발행 상태: 글(Post.publish_status)과 그 글을 넣은 곳(Placement.status)을 같이 움직인다 (2026-10-17 사용자:
  사용자가 직접 발행하고 발행 완료로 바꾼다). 글을 바꾸면 넣은 곳 모두, 넣은 곳을 바꾸면 모두 발행 완료일 때만 글도 발행 완료.
"""
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


def sync_post(post):
    """넣은 곳의 발행 상태가 바뀐 뒤: 모두 발행 완료면 글도 발행 완료, 하나라도 미발행이면 글은 미발행."""
    statuses = list(post.placements.values_list("status", flat=True))
    if statuses:
        _set_post(post, all(s == Placement.Status.PUBLISHED for s in statuses))
