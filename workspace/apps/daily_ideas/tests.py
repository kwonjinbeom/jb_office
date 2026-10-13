from django.test import TestCase
from django.urls import reverse

from apps.core.menus import get_menus
from apps.ideas.models import Idea


class DailyIdeasTests(TestCase):
    def test_daily_grid_loads_tracked_research(self):
        response = self.client.get(reverse("daily_ideas:list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "2026-10-14")
        self.assertContains(response, "CSV·엑셀 셀 단위 변경 검수기")
        self.assertContains(response, "36개")

    def test_adopt_copies_daily_item_to_my_ideas_once(self):
        Idea.objects.create(code="C35", title="기존 아이디어")
        url = reverse("daily_ideas:adopt", args=["20261014-01"])

        response = self.client.post(url)

        self.assertEqual(response.status_code, 302)
        idea = Idea.objects.get(code="C36")
        self.assertEqual(idea.code, "C36")
        self.assertEqual(idea.title, "CSV·엑셀 셀 단위 변경 검수기")
        self.assertIn("daily:20261014-01", idea.tags)

        self.client.post(url)
        self.assertEqual(Idea.objects.count(), 2)

    def test_navigation_separates_daily_and_my_ideas(self):
        titles = [menu.title for menu in get_menus()]

        self.assertEqual(titles[:2], ["일일 아이디어", "내 아이디어"])

    def test_my_ideas_grid_has_no_status_or_stars(self):
        Idea.objects.create(code="C01", title="표시 점검")

        response = self.client.get(reverse("ideas:list"))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "★")
        self.assertNotContains(response, ">상태<")
        self.assertContains(response, "내 아이디어")
