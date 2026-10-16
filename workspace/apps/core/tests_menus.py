from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse

from .menus import build_nav, get_menus
from .models import MenuSetting

URL = reverse("admin:core_menusetting_changelist")  # 관리화면 › 메뉴 › 메뉴 권한


class MenuPermissionPageTests(TestCase):
    """예전 '메뉴 관리'는 관리화면 안의 '메뉴 권한'으로 옮겼다 (이름·순서·보이기 + 볼 수 있는 그룹)."""

    def setUp(self):
        self.client.force_login(get_user_model().objects.create_superuser("admin1", password="pw-test-1234"))

    def keys(self):
        return [m.key for m in get_menus()]

    def test_blog_has_no_listing_child(self):
        blog = next(n for n in build_nav("") if n["menu"].key == "blog")
        self.assertNotIn("블로그·카페 리스트", [c["menu"].title for c in blog["children"]])
        self.assertEqual(blog["children"][0]["menu"].key, "blog_rules")

    def test_admin_index_has_only_auth_and_menu(self):
        res = self.client.get(reverse("admin:index"))
        self.assertContains(res, "메뉴 권한")
        self.assertContains(res, reverse("admin:auth_user_changelist"))
        for gone in ("/admin/memos/", "/admin/ideas/", "/admin/tasks/", "/admin/evidence/"):
            self.assertNotContains(res, gone)  # 다른 데이터는 관리화면에서 뺐다
        self.assertNotContains(self.client.get(reverse("core:home")), "메뉴 관리")  # 밖(사이드바)에는 없다

    def test_page_lists_menus(self):
        res = self.client.get(URL)
        self.assertEqual(res.status_code, 200)
        for text in ["메뉴 권한", "일일루틴", "블로그·카페", 'name="show_blog"', "볼 수 있는 그룹"]:
            self.assertContains(res, text)

    def test_save_rename_reorder_hide_then_reset(self):
        default = self.keys()
        order = ["blog", "routines", *[k for k in default if k not in ("blog", "routines")]]
        children = {"blog": ["blog_ops", "blog_rules", "posts", "blog_types", "site_templates", "blog_discussions"]}
        posted = []
        for key in order:
            posted.append(key)
            posted += children.get(key, [c.key for m in get_menus() if m.key == key for c in m.children])
        data = {"key": posted, **{f"show_{k}": "on" for k in posted if k != "memos"}, "title_routines": "루틴"}
        self.client.post(URL, data)
        menus = get_menus()
        self.assertEqual([m.key for m in menus][:2], ["blog", "routines"])
        self.assertEqual(menus[1].title, "루틴")
        self.assertNotIn("memos", [m.key for m in menus])  # 숨김
        self.assertEqual([c.key for c in menus[0].children][:2], ["blog_ops", "blog_rules"])
        self.assertEqual(MenuSetting.objects.get(key="blog").title, "")  # 기본 이름이면 비워 둔다
        self.assertContains(self.client.get(reverse("core:home")), "루틴")
        self.assertContains(self.client.get(URL), 'name="show_memos"')  # 숨긴 것도 권한 화면엔 보인다
        self.client.post(URL, {"action": "reset"})
        self.assertFalse(MenuSetting.objects.exists())
        self.assertEqual(self.keys(), default)


class MenuGroupPermissionTests(TestCase):
    def setUp(self):
        self.writers = Group.objects.create(name="글쓴이")
        self.admin = get_user_model().objects.create_superuser("admin1", password="pw-test-1234")
        self.member = get_user_model().objects.create_user("member", password="pw-test-1234")
        self.guest = get_user_model().objects.create_user("guest", password="pw-test-1234")
        self.member.groups.add(self.writers)
        self.client.force_login(self.admin)
        keys = [k for menu in get_menus() for k in (menu.key, *[c.key for c in menu.children])]
        data = {"key": keys, **{f"show_{k}": "on" for k in keys}, "groups_memos": [str(self.writers.pk)]}
        self.client.post(URL, data)  # 메모는 '글쓴이' 그룹만

    def test_menu_hidden_and_blocked_for_other_users(self):
        self.client.force_login(self.guest)
        self.assertNotIn("memos", [n["menu"].key for n in self.client.get(reverse("core:home")).context["NAV"]])
        self.assertEqual(self.client.get(reverse("memos:list")).status_code, 403)
        self.assertEqual(self.client.get(reverse("core:home")).status_code, 200)  # 메뉴가 아닌 화면은 그대로

    def test_group_member_and_superuser_see_it(self):
        self.client.force_login(self.member)
        self.assertIn("memos", [n["menu"].key for n in self.client.get(reverse("core:home")).context["NAV"]])
        self.assertEqual(self.client.get(reverse("memos:list")).status_code, 200)
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(reverse("memos:list")).status_code, 200)


class AdminSkinTests(TestCase):
    def test_admin_is_called_관리화면_with_app_style(self):
        self.client.force_login(get_user_model().objects.create_superuser("admin1", password="pw-test-1234"))
        res = self.client.get("/admin/")
        self.assertContains(res, "관리화면")
        self.assertContains(res, "css/admin.css")
        self.assertNotContains(res, "Django 관리")
