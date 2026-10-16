import shutil
import tempfile
from pathlib import Path

from django.conf import settings
from django.test import TestCase
from django.urls import reverse

from apps.core.menus import get_menus
from apps.ideas.models import Idea


class DailyIdeasTests(TestCase):
    """10-13 조사 파일 하나만 있는 폴더로 본다. 매일 새 날짜가 쌓여도 테스트가 흔들리지 않게."""

    def setUp(self):
        folder = Path(tempfile.mkdtemp(prefix="daily-"))
        self.addCleanup(shutil.rmtree, folder, True)
        shutil.copy(Path(settings.DAILY_IDEAS_DIR) / "2026-10-13.json", folder / "2026-10-13.json")
        override = self.settings(DAILY_IDEAS_DIR=folder)
        override.enable()
        self.addCleanup(override.disable)

    def test_daily_grid_loads_tracked_research(self):
        response = self.client.get(reverse("daily_ideas:list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "2026-10-13")
        self.assertContains(response, "CSV·엑셀 셀 단위 변경 검수기")
        self.assertContains(response, "36개")

    def test_adopt_copies_daily_item_to_my_ideas_once(self):
        Idea.objects.create(code="C35", title="기존 아이디어")
        url = reverse("daily_ideas:adopt", args=["20261013-01"])

        response = self.client.post(url)

        self.assertEqual(response.status_code, 302)
        idea = Idea.objects.get(code="C36")
        self.assertEqual(idea.code, "C36")
        self.assertEqual(idea.title, "CSV·엑셀 셀 단위 변경 검수기")
        self.assertIn("daily:20261013-01", idea.tags)

        self.client.post(url)
        self.assertEqual(Idea.objects.count(), 2)

    def test_calendar_moves_between_days_and_keeps_empty_days(self):
        response = self.client.get(reverse("daily_ideas:list"))
        calendar = response.context["calendar"]
        self.assertEqual(response.context["selected_date"], "2026-10-13")
        self.assertEqual([d["weekday"] for d in calendar["days"]], list("월화수목금토일"))
        picked = next(d for d in calendar["days"] if d["is_selected"])
        self.assertEqual((picked["iso"], picked["count"]), ("2026-10-13", 36))

        # 조사가 없는 날을 골라도 그 날짜에 머물고, 화살표는 조사한 날로 이어진다.
        response = self.client.get(reverse("daily_ideas:list"), {"date": "2026-10-10"})
        self.assertEqual(response.context["selected_date"], "2026-10-10")
        self.assertFalse(response.context["has_research"])
        self.assertEqual(response.context["calendar"]["next_date"], "2026-10-13")
        self.assertContains(response, "조사한 아이디어가 없습니다")

        self.assertEqual(self.client.get(reverse("daily_ideas:list"), {"date": "없는날짜"}).context["selected_date"], "2026-10-13")
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

        self.assertEqual(titles[:3], ["일일루틴", "일일 아이디어", "내 아이디어"])  # 일일루틴이 맨 위

    def test_my_ideas_grid_has_no_status_or_stars(self):
        Idea.objects.create(code="C01", title="표시 점검")

        response = self.client.get(reverse("ideas:list"))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "★")
        self.assertNotContains(response, ">상태<")
        self.assertContains(response, "내 아이디어")


class SearchStandardTests(TestCase):
    def test_first_visit_shows_default_sections_and_no_request_yet(self):
        response = self.client.get(reverse("daily_ideas:standard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "목적과 방향")
        self.assertContains(response, "첫 수익")  # 기본 문장으로 채워 둔다
        self.assertContains(response, "먼저 저장하면")
        self.assertEqual(response.context["request_text"], "")
        active = [c["menu"].key for n in response.context["NAV"] for c in n["children"] if c["active"]]
        self.assertEqual(active, ["daily_standard"])

    def test_saving_makes_versions_only_when_something_changed(self):
        from .models import SearchStandard
        from .standard import defaults

        url = reverse("daily_ideas:standard")
        data = {**defaults(), "focus": "itch.io 도구만 15개", "note": "첫 표준"}
        self.client.post(url, data)
        self.client.post(url, data)  # 그대로 다시 저장 → 새 버전 없음
        self.assertEqual(list(SearchStandard.objects.values_list("version", flat=True)), [1])

        self.client.post(url, {**data, "focus": "리그 오브 레전드 후보 2개 이상", "note": "주문 변경"})
        latest = SearchStandard.latest()
        self.assertEqual(latest.version, 2)

        response = self.client.get(url, {"for": "2026-10-14"})
        text = response.context["request_text"]
        self.assertIn("2026-10-14 일일 아이디어", text)
        self.assertIn('"standard_version": 2', text)
        self.assertIn("리그 오브 레전드 후보 2개 이상", text)

        # 옛 버전을 불러오면 그 내용이 폼에 들어오고, 요청문도 그 버전 기준이다.
        response = self.client.get(url, {"v": 1})
        self.assertEqual(response.context["viewing"].version, 1)
        self.assertIn("itch.io 도구만 15개", response.context["request_text"])

        md = self.client.get(reverse("daily_ideas:standard_md"), {"v": 1})
        self.assertEqual(md["Content-Type"], "text/markdown; charset=utf-8")
        self.assertIn("## 1. 목적과 방향", md.content.decode("utf-8"))

    def test_daily_page_shows_which_standard_was_used(self):
        response = self.client.get(reverse("daily_ideas:list"))
        self.assertContains(response, "표준 없이 조사")
        self.assertContains(response, reverse("daily_ideas:standard"))


class SearchMethodTests(TestCase):
    """10-14 조사 방식: 표준의 '조사 방식' 항목과, 서버의 기존 표준에 새 버전으로 반영하는 migration."""

    def test_migration_adds_a_version_keeping_what_the_user_wrote(self):
        import importlib

        from django.apps import apps as registry

        from . import standard
        from .models import SearchStandard

        migration = importlib.import_module("apps.daily_ideas.migrations.0002_searchstandard_approach")
        migration.forward(registry, None)  # 저장된 표준이 없으면 아무것도 만들지 않는다
        self.assertEqual(SearchStandard.objects.count(), 0)

        SearchStandard.objects.create(version=1, goal="내 목적", profile="내 조건", areas="내 분야", exclude="성인물만", focus="오늘 주문", criteria="옛 기준", output="30개")
        migration.forward(registry, None)
        latest = SearchStandard.latest()
        self.assertEqual(latest.version, 2)
        self.assertEqual((latest.goal, latest.profile, latest.areas, latest.exclude, latest.focus), ("내 목적", "내 조건", "내 분야", "성인물만", "오늘 주문"))
        self.assertEqual((latest.approach, latest.criteria, latest.output), (standard.APPROACH, standard.CRITERIA, standard.OUTPUT))
        self.assertEqual(SearchStandard.objects.get(version=1).criteria, "옛 기준")  # 옛 버전은 그대로 남는다

    def test_request_points_to_the_method_doc_and_includes_the_approach(self):
        self.client.post(reverse("daily_ideas:standard"), {**__import__("apps.daily_ideas.standard", fromlist=["defaults"]).defaults(), "note": "첫 표준"})
        text = self.client.get(reverse("daily_ideas:standard")).context["request_text"]
        self.assertIn("시장조사/00_아이디어_조사방법.md", text)
        self.assertIn("## 2. 조사 방식", text)
        self.assertIn("수익 경로가 서지 않으면", text)


class StayOnPageTests(TestCase):
    """담기·로그 기록은 화면을 옮기지 않는다 (사용자 요청 2026-10-14)."""

    def setUp(self):
        folder = Path(tempfile.mkdtemp(prefix="daily-"))
        self.addCleanup(shutil.rmtree, folder, True)
        shutil.copy(Path(settings.DAILY_IDEAS_DIR) / "2026-10-13.json", folder / "2026-10-13.json")
        override = self.settings(DAILY_IDEAS_DIR=folder)
        override.enable()
        self.addCleanup(override.disable)

    def test_adopt_answers_in_place_and_falls_back_to_the_same_list(self):
        url = reverse("daily_ideas:adopt", args=["20261013-01"])
        response = self.client.post(url, HTTP_X_REQUESTED_WITH="fetch")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        idea = Idea.objects.get()
        self.assertEqual((data["ok"], data["code"], data["url"]), (True, idea.code, idea.get_absolute_url()))

        # 다시 담으면 '이미 담김' 을 알려 주고 새로 만들지 않는다
        again = self.client.post(url, HTTP_X_REQUESTED_WITH="fetch").json()
        self.assertIn("이미 담긴", again["message"])
        self.assertEqual(Idea.objects.count(), 1)

        # 자바스크립트가 없을 때: 보던 목록으로 돌아간다 (내 아이디어 화면으로 가지 않는다)
        back = self.client.post(reverse("daily_ideas:adopt", args=["20261013-02"]), {"next": "/daily-ideas/?date=2026-10-13#idea-20261013-02"})
        self.assertEqual(back["Location"], "/daily-ideas/?date=2026-10-13#idea-20261013-02")
        evil = self.client.post(reverse("daily_ideas:adopt", args=["20261013-03"]), {"next": "https://evil.example/"})
        self.assertTrue(evil["Location"].startswith("/daily-ideas/?date=2026-10-13#idea-20261013-03"))

    def test_idea_list_folds_out_logs_and_takes_a_quick_log(self):
        from apps.ideas.models import IdeaLog

        idea = Idea.objects.create(code="C01", title="로그 점검")
        IdeaLog.objects.create(idea=idea, body="첫 기록")
        page = self.client.get(reverse("ideas:list"))
        self.assertContains(page, 'id="logs-%d"' % idea.pk)
        self.assertContains(page, "첫 기록")
        self.assertContains(page, 'data-ajax="log"')

        add = reverse("ideas:log_add", args=[idea.pk])
        data = self.client.post(add, {"body": "목록에서 적음"}, HTTP_X_REQUESTED_WITH="fetch").json()
        self.assertEqual((data["ok"], data["count"], data["log"]["body"]), (True, 2, "목록에서 적음"))
        bad = self.client.post(add, {"body": ""}, HTTP_X_REQUESTED_WITH="fetch")
        self.assertEqual(bad.status_code, 400)
        fallback = self.client.post(add, {"body": "폼으로 적음", "next": "/ideas/#logs-%d" % idea.pk})
        self.assertEqual(fallback["Location"], "/ideas/#logs-%d" % idea.pk)
        self.assertEqual(idea.logs.count(), 3)
