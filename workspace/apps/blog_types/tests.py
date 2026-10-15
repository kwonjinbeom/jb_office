from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Category, PostType, Section, SubType

INDEX = reverse("blog_types:index")


class BlogTypesTests(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_user("tester", password="pw-test-1234")
        self.client.force_login(user)

    @staticmethod
    def cat(code):
        """판매 수익 (커넥트)의 카테고리. 기호는 대분류마다 A 부터라 대분류를 함께 지정한다."""
        return Category.objects.get(section__name="판매 수익 (커넥트)", code=code)

    def test_seed_from_08(self):
        # 0002 migration 이 08 문서 표를 넣는다 (테스트 DB 도 migrate 로 만든다)
        # 0004: A~G 는 첫 대분류 '판매 수익 (커넥트)' 아래로 간다
        connect = Section.objects.get(name="판매 수익 (커넥트)")
        self.assertEqual(list(connect.categories.values_list("code", flat=True)), list("ABCDEFG"))
        self.assertEqual(connect.name, "판매 수익 (커넥트)")
        self.assertEqual(connect.categories.count(), 7)
        self.assertEqual(PostType.objects.filter(category__section=connect).count(), 14)
        self.assertEqual(self.cat("G").platform, Category.Platform.NAVER)
        season = PostType.objects.get(name="시즌 달력")
        self.assertEqual([s.name for s in season.subs.all()], ["세일 행사", "계절 품목", "기념일·시험"])

    def test_tree_shows_names_only_and_menu(self):
        res = self.client.get(INDEX)
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "판매 수익 (커넥트)")
        self.assertContains(res, "문제 해결")
        self.assertContains(res, "시즌 달력")
        self.assertContains(res, "세일 행사")  # 3단계까지 트리에 보인다
        self.assertNotContains(res, "K-세일페스타")  # 하위 설명은 트리에 없다
        self.assertContains(res, "왼쪽에서 하나를 고르세요")
        self.assertContains(res, "타입·카테고리")  # 블로그·카페 아래 중메뉴

    def test_select_shows_path_children_and_detail(self):
        season = PostType.objects.get(name="시즌 달력")
        res = self.client.get(INDEX, {"sel": season.sel})
        self.assertEqual(res.context["path"], [("판매 수익 (커넥트)", season.category.section.sel),
                                               ("C. 타이밍", season.category.sel), ("시즌 달력", season.sel)])
        self.assertEqual(res.context["open"], {season.category.section.sel, season.category.sel, season.sel})
        self.assertEqual(res.context["child_kind"], "sub")
        self.assertContains(res, "+ 하위 추가")
        sub = season.subs.first()
        res = self.client.get(INDEX, {"sel": sub.sel})
        self.assertContains(res, "K-세일페스타")  # 들어가면 설명이 보인다
        self.assertIsNone(res.context["child_kind"])

    def test_quick_add_each_level(self):
        res = self.client.post(reverse("blog_types:add", args=["section"]), {"name": "일상·브이로그"})
        daily = Section.objects.get(name="일상·브이로그")
        self.assertRedirects(res, f"{INDEX}?sel={daily.sel}", fetch_redirect_response=False)
        self.client.post(reverse("blog_types:add", args=["category"]), {"name": "카페", "parent": daily.sel})
        self.assertEqual(daily.categories.get().code, "A")  # 기호는 대분류마다 A 부터
        connect = Section.objects.get(name="판매 수익 (커넥트)")
        res = self.client.post(reverse("blog_types:add", args=["category"]), {"name": "구독", "parent": connect.sel})
        h = Category.objects.get(name="구독")
        self.assertEqual(h.code, "H")
        self.assertRedirects(res, f"{INDEX}?sel={h.sel}", fetch_redirect_response=False)
        self.client.post(reverse("blog_types:add", args=["type"]), {"name": "해지 비교", "parent": h.sel})
        t = h.types.get()
        self.client.post(reverse("blog_types:add", args=["sub"]), {"name": "OTT", "parent": t.sel})
        self.client.post(reverse("blog_types:add", args=["sub"]), {"name": "멤버십", "parent": t.sel})
        self.assertEqual([s.name for s in t.subs.all()], ["OTT", "멤버십"])
        # 단계가 안 맞으면(카테고리 밑에 하위, 부모 없는 카테고리) 넣지 않는다
        self.client.post(reverse("blog_types:add", args=["sub"]), {"name": "잘못", "parent": h.sel})
        self.client.post(reverse("blog_types:add", args=["category"]), {"name": "고아"})
        self.assertFalse(SubType.objects.filter(name="잘못").exists())
        self.assertFalse(Category.objects.filter(name="고아").exists())

    def test_move_reorders_siblings(self):
        season = PostType.objects.get(name="시즌 달력")
        last = season.subs.last()
        self.client.post(reverse("blog_types:move", args=["sub", last.pk]), {"dir": "up", "back": season.sel})
        self.assertEqual([s.name for s in season.subs.all()], ["세일 행사", "기념일·시험", "계절 품목"])
        first_cat = self.cat("A")
        self.client.post(reverse("blog_types:move", args=["category", first_cat.pk]), {"dir": "up"})
        self.assertEqual(first_cat.section.categories.first().code, "A")  # 맨 위는 더 못 올라간다
        daily = Section.objects.create(name="일상·브이로그", order=9)
        self.client.post(reverse("blog_types:move", args=["section", daily.pk]), {"dir": "up"})
        self.assertEqual([g.name for g in Section.objects.all()], ["판매 수익 (커넥트)", "일상·브이로그", "광고 수익 (조회수)"])

    def test_save_detail(self):
        sub = SubType.objects.get(name="세일 행사")
        res = self.client.post(reverse("blog_types:save", args=["sub", sub.pk]), {"name": "큰 세일", "note": "블프 위주"})
        self.assertRedirects(res, f"{INDEX}?sel={sub.sel}", fetch_redirect_response=False)
        sub.refresh_from_db()
        self.assertEqual((sub.name, sub.note), ("큰 세일", "블프 위주"))
        res = self.client.post(reverse("blog_types:save", args=["sub", sub.pk]), {"name": "", "note": ""})
        self.assertEqual(res.status_code, 200)  # 이름이 비면 저장하지 않고 오류를 보여 준다
        self.assertTrue(res.context["form"].errors)

    def test_delete_category_removes_children(self):
        c = self.cat("C")
        res = self.client.get(reverse("blog_types:delete", args=["category", c.pk]))
        self.assertContains(res, "타입 2개, 하위 3개")
        self.client.post(reverse("blog_types:delete", args=["category", c.pk]))
        self.assertFalse(SubType.objects.filter(name="세일 행사").exists())

    def test_delete_section_removes_everything_inside(self):
        connect = Section.objects.get(name="판매 수익 (커넥트)")
        res = self.client.get(reverse("blog_types:delete", args=["section", connect.pk]))
        self.assertContains(res, "카테고리 7개, 타입 14개, 하위 6개")
        self.client.post(reverse("blog_types:delete", args=["section", connect.pk]))
        self.assertFalse(Category.objects.filter(name="문제 해결").exists())
        self.assertEqual(Category.objects.count(), 8)  # 다른 대분류는 그대로

    def test_views_section_from_09(self):
        views = Section.objects.get(name="광고 수익 (조회수)")
        self.assertEqual(list(views.categories.values_list("code", flat=True)), list("ABCDEFGH"))
        finance = views.categories.get(name="금융·시장")
        daily = finance.types.get(name="일일 시황 · 오늘 ○○ 왜")
        self.assertEqual(daily.example_list, ["오늘 코스피 하락 이유", "나스닥 상승 이유"])
        self.assertIn("투자 권유 금지", finance.note)
        from importlib import import_module

        from django.apps import apps as django_apps

        import_module("apps.blog_types.migrations.0006_views_section").forward(django_apps, None)
        self.assertEqual(Section.objects.filter(name="광고 수익 (조회수)").count(), 1)  # 두 번 넣지 않는다

    def test_seed_does_not_overwrite(self):
        from importlib import import_module

        from django.apps import apps as django_apps

        seed = import_module("apps.blog_types.migrations.0002_seed_08").seed
        before = Category.objects.count()
        Category.objects.filter(section__name="판매 수익 (커넥트)", code="A").update(name="내가 바꾼 이름")
        seed(django_apps, None)
        self.assertEqual(Category.objects.count(), before)
        self.assertEqual(self.cat("A").name, "내가 바꾼 이름")
