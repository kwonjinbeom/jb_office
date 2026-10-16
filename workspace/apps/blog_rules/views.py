"""블로그·카페 › 규칙: 위에는 블로그 카드(하루 편수·쓰는 글·지표), 아래는 묶음별 규칙. 한 화면에서 보고 바로 고친다."""
from collections import OrderedDict

from django.contrib import messages
from django.db.models import Max
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from .forms import BlogForm, RuleForm
from .models import Blog, Rule


def _nav(request):
    request.nav_key = "blog_rules"


def index(request):
    _nav(request)
    blogs = list(Blog.objects.all())
    active = [b for b in blogs if b.status == Blog.Status.ACTIVE]
    accounts = OrderedDict()  # 같은 계정의 하루 편수 합계 (티스토리: 카카오 계정 단위로 합산된다)
    for b in active:
        if b.account:
            accounts.setdefault(b.account, []).append(b)
    groups = OrderedDict((value, {"label": label, "rules": []}) for value, label in Rule.Group.choices)
    for rule in Rule.objects.all():
        groups[rule.group]["rules"].append(rule)
    return render(request, "blog_rules/index.html", {
        "page_title": "규칙",
        "blogs": blogs,
        "daily_total": sum(b.daily for b in active),
        "accounts": [(name, sum(b.daily for b in items), items) for name, items in accounts.items() if len(items) > 1],
        "groups": groups,
    })


def blog_form(request, pk=None):
    _nav(request)
    blog = get_object_or_404(Blog, pk=pk) if pk else None
    form = BlogForm(request.POST or None, instance=blog)
    if request.method == "POST" and form.is_valid():
        saved = form.save(commit=False)
        if not blog:
            saved.order = (Blog.objects.aggregate(m=Max("order"))["m"] or 0) + 1
        saved.save()
        messages.success(request, f"'{saved.name}'을(를) 저장했습니다.")
        return redirect("blog_rules:index")
    return render(request, "blog_rules/form.html", {
        "page_title": "블로그 수정" if blog else "새 블로그", "form": form, "obj": blog, "kind": "blog",
    })


def rule_form(request, pk):
    _nav(request)
    rule = get_object_or_404(Rule, pk=pk)
    form = RuleForm(request.POST or None, instance=rule)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "규칙을 저장했습니다.")
        return redirect(f"{_index_url()}#g-{rule.group}")
    return render(request, "blog_rules/form.html", {"page_title": "규칙 수정", "form": form, "obj": rule, "kind": "rule"})


@require_POST
def rule_add(request):
    group, body = request.POST.get("group", ""), " ".join(request.POST.get("body", "").split())[:200]
    if group not in Rule.Group.values or not body:
        messages.warning(request, "규칙을 입력하세요.")
        return redirect("blog_rules:index")
    order = (Rule.objects.filter(group=group).aggregate(m=Max("order"))["m"] or 0) + 1
    Rule.objects.create(group=group, body=body, order=order)
    return redirect(f"{_index_url()}#g-{group}")


def delete(request, kind, pk):
    _nav(request)
    obj = get_object_or_404(Blog if kind == "blog" else Rule, pk=pk)
    if request.method == "POST":
        obj.delete()  # 휴지통으로 (7일 동안 복원 가능)
        messages.success(request, "휴지통으로 옮겼습니다.")
        return redirect("blog_rules:index")
    return render(request, "blog_rules/confirm_delete.html", {"page_title": "삭제", "obj": obj, "kind": kind})


def _index_url():
    return reverse("blog_rules:index")
