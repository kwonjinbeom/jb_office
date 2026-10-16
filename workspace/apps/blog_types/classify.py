"""글 분류 값: 티스토리·네이버 글쓰기의 글(Post)에 붙는 대분류 › 카테고리 › 타입 › 하위.

글에는 bt_category · bt_type · bt_sub 세 칸이 있고, 고른 가장 깊은 단계까지 채운다.
화면과 폼에서는 한 값으로 다룬다: "c3" (카테고리) · "t5" (타입) · "s9" (하위) · "" (미분류).
글쓰기 화면은 플랫폼에 맞는 카테고리만 고른다 (공통 + 티스토리 / 공통 + 네이버).
"""
from django.db.models import Q

from .models import Category, PostType, SubType

WRITERS = {"tistory": "티스토리 글쓰기", "naver": "네이버 글쓰기"}
UNCLASSIFIED = "미분류"


def post_model(writer):
    if writer == "naver":
        from apps.naver_writing.models import Post
    else:
        from apps.writing.models import Post
    return Post


def writer_of(post):
    return "naver" if post._meta.app_label == "naver_writing" else "tistory"


def categories_for(writer):
    platforms = [Category.Platform.ALL, Category.Platform.NAVER if writer == "naver" else Category.Platform.TISTORY]
    return Category.objects.filter(platform__in=platforms, section__deleted_at__isnull=True)


def choices(writer):
    """폼의 <select> 값: 대분류마다 묶고, 카테고리 › 타입 › 하위 순서로 펼친다."""
    cats = categories_for(writer).select_related("section").prefetch_related("types__subs")
    grouped = {}
    for cat in cats:
        rows = grouped.setdefault(cat.section, [])
        rows.append((f"c{cat.pk}", f"{cat.code}. {cat.name}"))
        for t in cat.types.all():
            rows.append((f"t{t.pk}", f"{cat.code}. {cat.name} › {t.name}"))
            for s in t.subs.all():
                rows.append((f"s{s.pk}", f"{cat.code}. {cat.name} › {t.name} › {s.name}"))
    sections = sorted(grouped, key=lambda s: (s.order, s.pk))
    return [("", UNCLASSIFIED)] + [(s.name, grouped[s]) for s in sections]


def _live(obj):
    return obj is not None and obj.deleted_at is None


def node_of(post):
    """살아 있는 가장 깊은 분류 단계. 중간 단계가 휴지통에 있으면 그 위까지만 본다."""
    cat = post.bt_category if post.bt_category_id else None
    if not _live(cat) or not _live(cat.section):
        return None
    t = post.bt_type if post.bt_type_id else None
    if not _live(t):
        return cat
    s = post.bt_sub if post.bt_sub_id else None
    return s if _live(s) else t


def value_of(post):
    node = node_of(post)
    return node.sel if node is not None else ""


def assign(post, value):
    """값 하나로 세 칸을 맞춘다. 모르는 값이면 미분류."""
    post.bt_category = post.bt_type = post.bt_sub = None
    kind, pk = (value or "")[:1], (value or "")[1:]
    if not pk.isdigit():
        return
    if kind == "s":
        sub = SubType.objects.filter(pk=pk).select_related("post_type__category").first()
        if sub:
            post.bt_sub, post.bt_type, post.bt_category = sub, sub.post_type, sub.post_type.category
    elif kind == "t":
        t = PostType.objects.filter(pk=pk).select_related("category").first()
        if t:
            post.bt_type, post.bt_category = t, t.category
    elif kind == "c":
        post.bt_category = Category.objects.filter(pk=pk).first()


def path_of(post):
    """[대분류, 'A. 카테고리', 타입, 하위] 중 있는 것만. 미분류면 []."""
    node = node_of(post)
    if node is None:
        return []
    cat = post.bt_category
    parts = [cat.section.name, f"{cat.code}. {cat.name}"]
    if isinstance(node, (PostType, SubType)):
        parts.append(post.bt_type.name)
    if isinstance(node, SubType):
        parts.append(post.bt_sub.name)
    return parts


def label_of(post):
    return " › ".join(path_of(post)) or UNCLASSIFIED


def sort_key(post):
    node = node_of(post)
    if node is None:
        return (1,)
    cat = post.bt_category
    key = [0, cat.section.order, cat.section.pk, cat.order, cat.code, cat.pk]
    if post.bt_type_id and isinstance(node, (PostType, SubType)):
        key += [post.bt_type.order, post.bt_type.pk]
    if isinstance(node, SubType):
        key += [post.bt_sub.order, post.bt_sub.pk]
    return tuple(key)


def grouped(posts):
    """글쓰기 목록용: 분류별로 묶는다. 분류 순서대로, 미분류는 맨 아래. 묶음 안의 순서는 그대로."""
    groups = {}
    for post in posts:
        groups.setdefault(label_of(post), {"label": label_of(post), "key": sort_key(post), "posts": []})["posts"].append(post)
    return sorted(groups.values(), key=lambda g: g["key"])


def with_classification(qs):
    return qs.select_related("bt_category__section", "bt_type", "bt_sub")


def node_filter(kind, obj):
    """글 분류 트리의 한 단계를 골랐을 때 그 아래 글 전부"""
    if kind == "section":
        return Q(bt_category__section=obj)
    if kind == "category":
        return Q(bt_category=obj)
    if kind == "type":
        return Q(bt_type=obj)
    if kind == "sub":
        return Q(bt_sub=obj)
    if kind == "unclassified":
        return unclassified_q()
    return Q()



class _Unclassified:
    """글 분류 트리의 '미분류' 칸. 대분류와 같은 줄에 있고, 분류가 없는 글(또는 분류가 휴지통에 간 글)이 모두 여기 든다."""
    name = UNCLASSIFIED
    sel = "u"
    pk = None
    deleted_at = None

    def __str__(self):
        return self.name


UNCLASSIFIED_NODE = _Unclassified()


def unclassified_q():
    return (Q(bt_category__isnull=True) | Q(bt_category__deleted_at__isnull=False)
            | Q(bt_category__section__deleted_at__isnull=False))


def class_tree():
    """글쓰기마다 대분류 › 카테고리 › 타입 › 하위 + 미분류, 그리고 그 아래 글 수 (발행 완료가 아닌 글: 임시·검토·포스트 모두).
    글 관리(글쓰기)와 글 매핑 관리 두 화면이 같은 트리를 쓴다."""
    from collections import Counter

    from .models import Section

    sections = list(Section.objects.prefetch_related("categories__types__subs"))
    writers = []
    for key, label in WRITERS.items():
        allowed = {c.pk for c in categories_for(key)}
        Post = post_model(key)
        counts = Counter()
        for post in with_classification(Post.objects.exclude(publish_status=Post.Publish.DONE)):
            counts["all"] += 1
            node = node_of(post)
            if node is None:
                counts["u"] += 1
                continue
            cat = post.bt_category
            counts[cat.section.sel] += 1
            counts[cat.sel] += 1
            if isinstance(node, (PostType, SubType)):
                counts[post.bt_type.sel] += 1
            if isinstance(node, SubType):
                counts[post.bt_sub.sel] += 1
        writers.append({"key": key, "label": label, "count": counts["all"], "unclassified": counts["u"], "sections": [
            {"obj": g, "count": counts[g.sel], "cats": [
                {"obj": c, "count": counts[c.sel], "types": [
                    {"obj": t, "count": counts[t.sel], "subs": [{"obj": s, "count": counts[s.sel]} for s in t.subs.all()]}
                    for t in c.types.all()]}
                for c in g.categories.all() if c.pk in allowed]}
            for g in sections]})
    return writers
