from django.test import TestCase

from apps.blog_rules.models import Blog, Rule
from apps.blog_types.models import Category, SiteCategory
from apps.core.models import TrashEntry


class SaleEventTests(TestCase):
    """0053 (2026-10-31 사용자): 10-27 정리 때 빠진 black_lukey › 세일 이벤트를 글쓰기·템플릿 구조 전체에서 되살린다."""

    def test_sale_event_is_back_everywhere(self):
        cat = Category.objects.get(section__name="black_lukey", name="세일 이벤트")
        self.assertIn("검색량 순", cat.direction)  # 0055: 고정 5곳 → 혜택 시즌 → 생활 혜택
        site_cat = SiteCategory.objects.get(blog__name="black_lukey", parent=None, name="세일 이벤트")
        self.assertIn("구매 타이밍", site_cat.concept)  # 다루지 않는 것까지 컨셉에
        self.assertIn("::: 제품 | 행사 이름", site_cat.concept)
        self.assertIn("자라(블프·시즌오프)", site_cat.concept)
        self.assertNotIn("코리아세일페스타처럼", site_cat.concept)  # 검색량이 낮아 고정에서 뺐다
        self.assertTrue(Rule.objects.filter(blog__name="black_lukey", body__startswith="올영·무신사 행사").exists())
        self.assertIn("인기 세일", Blog.objects.get(name="black_lukey").content)
        self.assertFalse(TrashEntry.objects.filter(title__contains="세일 이벤트").exists())  # 7일 뒤 영구 삭제되지 않게

    def test_daily_pick_and_design_sample(self):
        from apps.routines.views import default_picks
        from apps.site_templates.design_cats import CATS
        cat = Category.objects.get(section__name="black_lukey", name="세일 이벤트")
        self.assertIn(f"c{cat.pk}", default_picks(None))  # 글쓰기 '오늘 쓸 분류' 후보 (소재 판정에서 있을 때만 쓴다)
        self.assertIn(("black_lukey", "세일 이벤트"), CATS)
