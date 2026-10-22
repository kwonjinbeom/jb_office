from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.core.menus import find_menu

from .models import Event

INDEX = reverse("schedule:index")


class ScheduleTests(TestCase):
    def setUp(self):
        self.client.force_login(get_user_model().objects.create_user("tester", password="pw-test-1234"))

    def test_calendar_list_and_form(self):
        """큰 달력 + 고른 날 일정 + 입력 폼 (2026-10-22 사용자)"""
        self.assertEqual(find_menu("schedule").title, "일정관리")
        Event.objects.create(date=date(2026, 10, 22), title="회의", time="10:00")
        res = self.client.get(INDEX, {"m": "2026-10", "d": "2026-10-22"})
        self.assertEqual(res.context["ACTIVE_MENU"], "schedule")
        self.assertEqual(len(res.context["weeks"]), 5)  # 2026년 10월: 일요일 시작 5주
        self.assertContains(res, "<b>10:00</b> 회의", html=False)  # 달력 칸
        self.assertEqual([e.title for e in res.context["day_events"]], ["회의"])
        self.assertContains(res, 'value="2026-10-22"')  # 새 일정 폼의 날짜 = 고른 날
        self.assertContains(res, "블리치 천년혈전 50화")  # 처음 넣어 둔 일정 (10/28) 이 달력에

    def test_alarm_due_ack_and_reset(self):
        """시각이 된 일정만 알림, 누르면(ack) 다시 안 뜨고, 시각을 바꾸면 다시 뜬다 (2026-10-22 사용자)"""
        from datetime import timedelta
        from django.utils import timezone

        now = timezone.localtime()
        past = Event.objects.create(date=now.date(), time=(now - timedelta(minutes=1)).time(), title="지난 일정")
        Event.objects.create(date=now.date(), time=(now + timedelta(hours=1)).time() if now.hour < 23 else None, title="나중 일정")
        Event.objects.create(date=now.date(), title="종일 일정")
        ids = [a["id"] for a in self.client.get(reverse("schedule:alarms")).json()["alarms"]]
        self.assertEqual(ids, [past.pk])
        self.client.post(reverse("schedule:ack", args=[past.pk]))
        self.assertEqual(self.client.get(reverse("schedule:alarms")).json()["alarms"], [])
        self.client.post(reverse("schedule:save"), {"pk": past.pk, "date": past.date.isoformat(),
                                                    "time": (now - timedelta(minutes=2)).strftime("%H:%M"), "title": "지난 일정"})
        past.refresh_from_db()
        self.assertIsNone(past.alarm_ack)  # 시각을 바꾸면 다시 알린다
        self.assertContains(self.client.get(INDEX), "js/alarm.js")  # 모든 화면에 알림 스크립트

    def test_save_edit_done_delete(self):
        res = self.client.post(reverse("schedule:save"), {"date": "2026-11-02", "title": "원피스 1197화", "note": ""})
        self.assertRedirects(res, INDEX + "?m=2026-11&d=2026-11-02", fetch_redirect_response=False)
        e = Event.objects.get(title="원피스 1197화")
        self.client.post(reverse("schedule:save"), {"pk": e.pk, "date": "2026-11-03", "time": "09:30", "title": "원피스 1197화 확인"})
        e.refresh_from_db()
        self.assertEqual((e.date, e.title, e.time.hour), (date(2026, 11, 3), "원피스 1197화 확인", 9))
        res = self.client.get(INDEX, {"d": "2026-11-03", "e": e.pk})
        self.assertEqual(res.context["editing"], e)
        self.client.post(reverse("schedule:done", args=[e.pk]))
        e.refresh_from_db()
        self.assertTrue(e.done)
        self.client.post(reverse("schedule:delete", args=[e.pk]))
        self.assertFalse(Event.objects.filter(pk=e.pk).exists())
        self.assertTrue(Event.all_objects.filter(pk=e.pk).exists())  # 휴지통
