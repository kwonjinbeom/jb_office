"""공통 휴지통: 원본 + 인덱스된 삭제 시각, 작은 복원 연결 목록만 보관한다."""
from datetime import timedelta

from django.apps import apps
from django.db import models, transaction
from django.db.models.deletion import CASCADE, PROTECT, ProtectedError
from django.utils import timezone

from .models import SourceExclusion, TrashEntry


MODEL_SECTIONS = {
    "ideas.idea": "내 아이디어", "ideas.stage": "내 아이디어 · 단계",
    "ideas.idealog": "내 아이디어 · 작업 로그", "tasks.task": "할 일",
    "evidence.evidence": "증거", "memos.memo": "메모",
    "content.folder": "폴더", "content.content": "콘텐츠", "content.publication": "게시 기록",
    "discussions.discussion": "진행현황", "discussions.discussionhistory": "논의 이력",
    "daily_ideas.searchstandard": "검색 표준", "writing.post": "티스토리 글쓰기",
    "naver_writing.post": "네이버 글쓰기", "blog_types.section": "카테고리 관리 · 대분류",
    "blog_types.category": "카테고리 관리 · 카테고리",
    "blog_types.posttype": "카테고리 관리 · 타입", "blog_types.subtype": "카테고리 관리 · 하위",
    "blog_types.sitecategory": "카테고리 관리 · 사이트 카테고리", "blog_types.placement": "카테고리 관리 · 매핑",
    "blog_rules.blog": "운영 · 사이트", "blog_rules.rule": "운영 · 체크", "blog_ops.plan": "모니터링 · 발행 계획",
    "routines.routine": "일일루틴", "routines.evaluation": "일일루틴 · 평가", "routines.fixedtopic": "커스텀 글쓰기 · 고정 주제",
}
SOURCE_SECTIONS = {"daily": "일일 아이디어", "docs": "문서"}
OWNED = {("tasks.task", "idea"), ("evidence.evidence", "idea")}


class TrashError(ValueError):
    pass


def model_for(label):
    if label not in MODEL_SECTIONS:
        raise TrashError("삭제할 수 없는 항목입니다.")
    return apps.get_model(label)


def title_for(obj):
    for field in ("title", "name", "channel", "body"):
        value = getattr(obj, field, "")
        if value:
            return str(value)[:200]
    if hasattr(obj, "version"):
        return f"검색 표준 v{obj.version}"
    return f"{MODEL_SECTIONS.get(obj._meta.label_lower, '항목')} #{obj.pk}"


def section_for(obj):
    label = MODEL_SECTIONS[obj._meta.label_lower]
    if getattr(obj, "workspace", None):
        label = f"{obj.get_workspace_display()} · {label}"
    if obj._meta.label_lower in {"writing.post", "naver_writing.post"}:
        label += f" · {obj.get_stage_display()}"
    return label


def _owned_relations(model):
    for rel in model._meta.related_objects:
        if rel.related_model._meta.label_lower not in MODEL_SECTIONS:
            continue
        if rel.on_delete in (CASCADE, PROTECT) or (rel.related_model._meta.label_lower, rel.field.name) in OWNED:
            yield rel


def _collect(model, ids, *, live=True):
    found, queue = {}, [(model, list(ids))]
    while queue:
        current, keys = queue.pop()
        label = current._meta.label_lower
        fresh = set(keys) - set(found.get(label, []))
        if not fresh:
            continue
        qs = current.all_objects.filter(pk__in=fresh)
        if live:
            qs = qs.filter(deleted_at__isnull=True)
        fresh = list(qs.values_list("pk", flat=True))
        if not fresh:
            continue
        found.setdefault(label, []).extend(fresh)
        for rel in _owned_relations(current):
            children = rel.related_model.all_objects.filter(**{f"{rel.field.attname}__in": fresh})
            if live:
                children = children.filter(deleted_at__isnull=True)
            queue.append((rel.related_model, list(children.values_list("pk", flat=True))))
    return found


def _discussion_keys(members):
    ids = members.get("discussions.discussion", [])
    if not ids:
        return []
    return list(model_for("discussions.discussion").all_objects.filter(pk__in=ids).exclude(doc="").values_list("doc", flat=True))


@transaction.atomic
def move_to_trash(obj):
    model = model_for(obj._meta.label_lower)
    # Recheck inside the transaction: retries/double clicks must never create two entries.
    if not model.all_objects.filter(pk=obj.pk, deleted_at__isnull=True).exists():
        return None
    now = timezone.now()
    members = _collect(model, [obj.pk])
    entry = TrashEntry.objects.create(model_label=obj._meta.label_lower, object_key=str(obj.pk),
                                      title=title_for(obj), section=section_for(obj), deleted_at=now, members=members)
    for label, ids in members.items():
        model_for(label).all_objects.filter(pk__in=ids, deleted_at__isnull=True).update(deleted_at=now)
    SourceExclusion.objects.bulk_create([SourceExclusion(kind="discussion", key=key) for key in _discussion_keys(members)], ignore_conflicts=True)
    return entry


@transaction.atomic
def move_queryset(queryset):
    count, labels = 0, {}
    for obj in list(queryset):
        entry = move_to_trash(obj)
        if entry:
            count += 1
            labels[obj._meta.label] = labels.get(obj._meta.label, 0) + 1
    return count, labels


@transaction.atomic
def hide_source(kind, key, title):
    if kind not in SOURCE_SECTIONS:
        raise TrashError("삭제할 수 없는 자료입니다.")
    exclusion, created = SourceExclusion.objects.get_or_create(kind=kind, key=key)
    if not created:
        return None
    return TrashEntry.objects.create(model_label=f"source.{kind}", object_key=key, title=title[:200],
                                     section=SOURCE_SECTIONS[kind], deleted_at=timezone.now())


def hidden_keys(kind):
    return set(SourceExclusion.objects.filter(kind=kind).values_list("key", flat=True))


@transaction.atomic
def restore(entry):
    entry = TrashEntry.objects.select_for_update().filter(pk=entry.pk).first()
    if entry is None:
        raise TrashError("항목이 이미 복원되었거나 보관 기간이 지났습니다.")
    if entry.expires_at <= timezone.now():
        raise TrashError("보관 기간 7일이 지나 복원할 수 없습니다.")
    if entry.model_label.startswith("source."):
        SourceExclusion.objects.filter(kind=entry.model_label.split(".", 1)[1], key=entry.object_key).delete()
    else:
        for label, ids in entry.members.items():
            model = model_for(label)
            rows = model.all_objects.filter(pk__in=ids, deleted_at=entry.deleted_at)
            for field in model._meta.fields:
                if not field.many_to_one or field.related_model._meta.label_lower not in MODEL_SECTIONS:
                    continue
                # Optional cross references survive deletion; ownership and required parents must be live.
                if field.null and field.remote_field.on_delete is not PROTECT and (label, field.name) not in OWNED:
                    continue
                parent_label = field.related_model._meta.label_lower
                parent_ids = rows.exclude(**{field.attname: None}).values_list(field.attname, flat=True)
                missing = field.related_model.all_objects.filter(pk__in=parent_ids, deleted_at__isnull=False)
                missing = missing.exclude(pk__in=entry.members.get(parent_label, []))
                if missing.exists():
                    raise TrashError("상위 항목이 휴지통에 있습니다. 상위 항목을 먼저 복원하세요.")
        keys = _discussion_keys(entry.members)
        for label, ids in entry.members.items():
            model_for(label).all_objects.filter(pk__in=ids, deleted_at=entry.deleted_at).update(deleted_at=None)
        SourceExclusion.objects.filter(kind="discussion", key__in=keys).delete()
    entry.delete()


@transaction.atomic
def _purge_entry(entry, cutoff):
    if entry.model_label.startswith("source."):
        entry.delete()  # Keep the tiny exclusion key so a Git source cannot reappear.
        return True
    # Never cascade through a live or more recently deleted child.
    graph = {}
    for label, ids in entry.members.items():
        for related, keys in _collect(model_for(label), ids, live=False).items():
            graph.setdefault(related, set()).update(keys)
    for label, ids in graph.items():
        if model_for(label).all_objects.filter(pk__in=ids).filter(models.Q(deleted_at__isnull=True) | models.Q(deleted_at__gt=cutoff)).exists():
            return False
    pending = [(model_for(label), pk) for label, ids in graph.items() for pk in ids]
    while pending:
        deferred, progressed = [], False
        for model, pk in pending:
            obj = model.all_objects.filter(pk=pk).first()
            if obj is None:
                progressed = True
                continue
            try:
                # PROTECT parents are retried after children; savepoints keep failed collectors isolated.
                with transaction.atomic():
                    models.Model.delete(obj)
                progressed = True
            except ProtectedError:
                deferred.append((model, pk))
        if deferred and not progressed:
            raise TrashError("연결된 항목 때문에 영구 삭제를 보류했습니다.")
        pending = deferred
    entry.delete()
    return True


def purge_expired(*, now=None, limit=50):
    cutoff = (now or timezone.now()) - timedelta(days=7)
    count = 0
    entries = TrashEntry.objects.filter(deleted_at__lte=cutoff).order_by("deleted_at", "pk")[:limit]
    for entry in list(entries):
        try:
            if _purge_entry(entry, cutoff):
                count += 1
        except TrashError:
            continue
    return count
