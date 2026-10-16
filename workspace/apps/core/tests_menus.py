from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .menus import build_nav, get_menus
from .models import MenuSetting

URL = reverse("core:menus")


class MenuManageTests(TestCase):
    def setUp(self):
        self.client.force_login(get_user_model().objects.create_user("tester", password="pw-test-1234"))

    def keys(self):
        return [m.key for m in get_menus()]

    def test_blog_has_no_listing_child(self):
        blog = next(n for n in build_nav("") if n["menu"].key == "blog")
        self.assertNotIn("블로그·카페 리스트", [c["menu"].title for c in blog["children"]])
        self.assertEqual(blog["children"][0]["menu"].key, "blog_rules")

    def test_page_lists_menus_and_sidebar_links(self):
        res = self.client.get(URL)
        self.assertEqual(res.status_code, 200)
        for text in ["메뉴 관리", "일일루틴", "아이디어", "블로그·카페", "관리화면", 'name="show_blog"']:
            self.assertContains(res, text)
        self.assertNotContains(res, "Django 관리자")

    def test_save_rename_reorder_hide_then_reset(self):
        default = self.keys()
        order = ["blog", "routines", *[k for k in default if k not in ("blog", "routines")]]
        # 블로그·카페 묶음 안에서는 '모니터링'을 '운영'보다 위로
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
        blog = menus[0]
        self.assertEqual([c.key for c in blog.children][:2], ["blog_ops", "blog_rules"])
        self.assertEqual(MenuSetting.objects.get(key="blog").title, "")  # 기본 이름이면 비워 둔다
        res = self.client.get(reverse("core:home"))
        self.assertContains(res, "루틴")
        self.assertContains(self.client.get(URL), 'name="show_memos"')  # 숨긴 것도 관리 화면엔 보인다
        self.client.post(URL, {"action": "reset"})
        self.assertFalse(MenuSetting.objects.exists())
        self.assertEqual(self.keys(), default)


class AdminSkinTests(TestCase):
    def test_admin_is_called_관리화면_with_app_style(self):
        self.client.force_login(get_user_model().objects.create_superuser("admin1", password="pw-test-1234"))
        res = self.client.get("/admin/")
        self.assertContains(res, "관리화면")
        self.assertContains(res, "css/admin.css")
        self.assertNotContains(res, "Django 관리")
