"""관리화면: '인증 및 권한'(사용자·그룹)과 '메뉴 › 메뉴 권한'만 둔다 (2026-10-16 사용자).

메뉴 권한 = 예전 '메뉴 관리' 화면(이름·순서·보이기)을 관리화면 안으로 옮기고, 메뉴마다 볼 수 있는 그룹을 더한 것.
한 화면에서 모든 메뉴를 고친다 (줄마다 들어가는 기본 목록 대신).
"""
from django.contrib import admin, messages
from django.contrib.auth.models import Group
from django.shortcuts import redirect
from django.template.response import TemplateResponse

from .menus import MENUS, _settings, all_menus
from .models import MenuSetting


@admin.register(MenuSetting)
class MenuPermissionAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        if not self.has_change_permission(request):
            return super().changelist_view(request, extra_context)
        defaults = {m.key: m.title for menu in MENUS for m in (menu, *menu.children)}
        groups = list(Group.objects.order_by("name"))
        if request.method == "POST":
            if request.POST.get("action") == "reset":
                MenuSetting.objects.all().delete()
                messages.success(request, "메뉴를 기본값으로 되돌렸습니다 (이름·순서·보이기·그룹).")
                return redirect(request.path)
            keys = [k for k in request.POST.getlist("key") if k in defaults]
            group_ids = {g.pk for g in groups}
            for order, key in enumerate(keys, start=1):
                title = " ".join(request.POST.get(f"title_{key}", "").split())[:40]
                setting, _ = MenuSetting.objects.update_or_create(key=key, defaults={
                    "title": "" if title == defaults[key] else title,
                    "order": order * 10,
                    "hidden": f"show_{key}" not in request.POST,
                })
                picked = [int(v) for v in request.POST.getlist(f"groups_{key}") if v.isdigit() and int(v) in group_ids]
                setting.groups.set(picked)
            messages.success(request, "메뉴 권한을 저장했습니다. 왼쪽 메뉴와 홈에 바로 반영됩니다.")
            return redirect(request.path)
        saved = _settings()
        rows = []
        for menu in all_menus():
            for m in (menu, *menu.children):
                s = saved.get(m.key)
                rows.append({"menu": m, "child": m is not menu, "top_key": menu.key, "default": defaults.get(m.key, m.title),
                             "hidden": bool(s and s.hidden), "group_ids": getattr(s, "group_ids", set()) if s else set(),
                             "url": m.url})
        context = {
            **self.admin_site.each_context(request),
            "title": "메뉴 권한", "subtitle": None, "opts": self.model._meta, "rows": rows, "groups": groups,
            "changed": bool(saved), **(extra_context or {}),
        }
        return TemplateResponse(request, "admin/core/menu_permissions.html", context)
