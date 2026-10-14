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

    def test_calendar_moves_between_days_and_keeps_empty_days(self):
        response = self.client.get(reverse("daily_ideas:list"))
        calendar = response.context["calendar"]
        self.assertEqual(response.context["selected_date"], "2026-10-14")
        self.assertEqual([d["weekday"] for d in calendar["days"]], list("월화수목금토일"))
        picked = next(d for d in calendar["days"] if d["is_selected"])
        self.assertEqual((picked["iso"], picked["count"]), ("2026-10-14", 36))

        # 조사가 없는 날을 골라도 그 날짜에 머물고, 화살표는 조사한 날로 이어진다.
        response = self.client.get(reverse("daily_ideas:list"), {"date": "2026-10-10"})
        self.assertEqual(response.context["selected_date"], "2026-10-10")
        self.assertFalse(response.context["has_research"])
        self.assertEqual(response.context["calendar"]["next_date"], "2026-10-14")
        self.assertContains(response, "조사한 아이디어가 없습니다")

        self.assertEqual(self.client.get(reverse("daily_ideas:list"), {"date": "없는날짜"}).context["selected_date"], "2026-10-14")
        self.assertTrue(self.client.get(reverse("daily_ideas:list"), {"date": "all"}).context["show_all"])

    def test_rows_show_idea_and_detail_with_plan_behind_a_click(self):
        response = self.client.get(reverse("daily_ideas:list"), {"category": "tool", "q": "CSV"})
        item = response.context["groups"][0]["items"][0]

        self.assertEqual([step["title"] for step in item["plan_steps"]], ["만들 것", "첫 검증", "알릴 곳", "돈 받는 방식"])
        self.assertContains(response, "구현 계획")
        self.assertContains(response, '<details class="il-row"')
        self.assertNotContains(response, "돈의 흐름")  # 예전 표의 열 제목
        # 날짜를 옮겨도 검색어·분류가 따라간다.
        self.assertIn("category=tool", response.context["keep"])

    def test_plan_field_overrides_default_steps(self):
        from .data import _plan_steps

        steps = _plan_steps({"plan": ["화면 하나 만들기", {"title": "2주차", "detail": "가격 묻기"}], "min_product": "무시"})
        self.assertEqual(steps, [{"title": "", "detail": "화면 하나 만들기"}, {"title": "2주차", "detail": "가격 묻기"}])

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
