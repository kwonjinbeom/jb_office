from unittest.mock import patch
from django.core.exceptions import ValidationError
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from .forms import DiscussionForm
from .models import Discussion


@override_settings(REQUIRE_LOGIN=False)
class DiscussionTests(TestCase):
    def setUp(self):
        patcher = patch("apps.core.context_processors.gitstate.deploy_status", return_value=None)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.root = Discussion.objects.create(area="blog", name="제품 비교")
        self.child = Discussion.objects.create(area="blog", name="AI 도구", parent=self.root)
        self.deep = Discussion.objects.create(area="blog", name="글 템플릿", parent=self.child, summary="비교 기준부터 정하기", next_action="샘플 검토", partner="codex", amount="several")

    def test_nested_filter_and_short_grid(self):
        response = self.client.get(reverse("discussions:list"), {"topic": self.root.pk, "q": "글 템플릿"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual([x.pk for x in response.context["entries"]], [self.deep.pk])
        self.assertContains(response, "제품 비교 / AI 도구 / 글 템플릿")
        self.assertContains(response, 'maxlength="140"')

    def test_cycle_cross_area_and_changing_parent_menu_are_rejected(self):
        self.root.parent = self.deep
        with self.assertRaises(ValidationError):
            self.root.full_clean()
        self.root.parent = None
        self.root.area = "video"
        with self.assertRaises(ValidationError):
            self.root.full_clean()
        other = Discussion.objects.create(area="video", name="영상")
        self.deep.parent = other
        with self.assertRaises(ValidationError):
            self.deep.full_clean()

    def test_create_edit_and_snapshot_only_on_real_changes(self):
        response = self.client.post(reverse("discussions:create"), {"area": "blog", "parent": self.child.pk, "name": "게시 주기", "summary": "주 1회 검토", "next_action": "카테고리 선택", "status": "talk", "amount": "little", "partner": "codex"})
        self.assertEqual(response.status_code, 302)
        item = Discussion.objects.get(name="게시 주기")
        self.assertEqual(item.history.count(), 1)
        url = reverse("discussions:quick", args=[item.pk])
        update = {"summary": "첫 글부터 완성", "next_action": "초안 검토", "status": "decided"}
        self.client.post(url, update)
        self.assertEqual(item.history.count(), 2)
        self.client.post(url, update)
        self.assertEqual(item.history.count(), 2)
        item.refresh_from_db()
        self.assertEqual(item.partner, "codex")
        self.assertEqual(item.history.last().summary, "주 1회 검토")
        for name, args in [("list", []), ("create", []), ("detail", [item.pk]), ("edit", [item.pk]), ("delete", [item.pk])]:
            self.assertEqual(self.client.get(reverse(f"discussions:{name}", args=args)).status_code, 200)

    def test_overlong_summary_does_not_save_and_csrf_is_required(self):
        url = reverse("discussions:quick", args=[self.deep.pk])
        self.assertEqual(self.client.get(url).status_code, 405)
        self.client.post(url, {"summary": "가" * 141, "next_action": "검토", "status": "talk"})
        self.deep.refresh_from_db()
        self.assertEqual(self.deep.summary, "비교 기준부터 정하기")
        self.assertEqual(self.deep.history.count(), 0)
        self.assertEqual(Client(enforce_csrf_checks=True).post(url, {"summary": "변경", "status": "talk"}).status_code, 403)

    def test_delete_parent_is_protected(self):
        self.client.post(reverse("discussions:delete", args=[self.root.pk]))
        self.assertTrue(Discussion.objects.filter(pk=self.root.pk).exists())
        form = DiscussionForm(instance=self.root)
        choices = [value for value, _ in form.fields["parent"].choices]
        self.assertNotIn(self.deep.pk, choices)

    def test_menu_filter_discards_incompatible_topic_and_save_keeps_filters(self):
        other = Discussion.objects.create(area="video", name="첫 영상")
        response = self.client.get(reverse("discussions:list"), {"area": "video", "topic": self.root.pk})
        self.assertEqual([x.pk for x in response.context["entries"]], [other.pk])
        response = self.client.post(reverse("discussions:quick", args=[self.deep.pk]), {"summary": "비교 기준 확정", "next_action": "샘플 검토", "status": "decided", "return_to": "/discussions/?area=blog"})
        self.assertEqual(response["Location"], "/discussions/?area=blog")

    def test_blog_and_video_discussions_sit_under_their_menu_and_the_rest_is_progress(self):
        def active_keys(response):
            keys = [n["menu"].key for n in response.context["NAV"] if n["active"]]
            return keys + [c["menu"].key for n in response.context["NAV"] for c in n["children"] if c["active"]]

        # 전체 = 진행현황
        response = self.client.get(reverse("discussions:list"))
        self.assertEqual(active_keys(response), ["discussions"])
        self.assertContains(response, "진행현황")
        self.assertContains(response, ">메뉴</th>")

        # 블로그·카페 아래 논의 현황: 그 메뉴 것만, 메뉴 열은 없다.
        video = Discussion.objects.create(area="video", name="첫 영상")
        response = self.client.get(reverse("discussions:list"), {"area": "blog"})
        self.assertEqual(active_keys(response), ["blog_discussions"])
        self.assertTrue(next(n for n in response.context["NAV"] if n["menu"].key == "blog")["open"])
        self.assertNotIn(video.pk, [x.pk for x in response.context["entries"]])
        self.assertNotContains(response, ">메뉴</th>")

        # 상세·수정·새 주제도 같은 가지에 머문다.
        for url in [self.deep.get_absolute_url(), reverse("discussions:edit", args=[self.deep.pk]), reverse("discussions:create") + "?area=video"]:
            expected = "video_discussions" if "area=video" in url else "blog_discussions"
            self.assertEqual(active_keys(self.client.get(url)), [expected])

        # 하위 메뉴가 없는 영역은 진행현황에 남는다.
        other = Discussion.objects.create(area="other", name="공통 주제")
        self.assertEqual(active_keys(self.client.get(other.get_absolute_url())), ["discussions"])
        self.assertEqual(self.client.post(reverse("discussions:delete", args=[video.pk]))["Location"], "/discussions/?area=video")

    def test_dates_order_group_and_filter(self):
        from datetime import timedelta
        from django.utils import timezone
        from .models import DiscussionHistory

        now = timezone.now()
        # 루트는 9일 전, 자식은 2일 전에 바뀐 것으로 둔다 (auto_now 를 피해 update 로).
        Discussion.objects.filter(pk=self.root.pk).update(updated_at=now - timedelta(days=9), created_at=now - timedelta(days=20))
        Discussion.objects.filter(pk=self.child.pk).update(updated_at=now - timedelta(days=2))
        old_log = DiscussionHistory.objects.create(discussion=self.root, summary="열흘 전 요약", status="talk", amount="little", partner="codex")
        DiscussionHistory.objects.filter(pk=old_log.pk).update(created_at=now - timedelta(days=9))

        response = self.client.get(reverse("discussions:list"))
        self.assertEqual([x.pk for x in response.context["entries"]], [self.deep.pk, self.child.pk, self.root.pk])  # 최신 변경이 위
        self.assertEqual([g["label"] for g in response.context["day_groups"]][0], "오늘")
        self.assertEqual(len(response.context["day_groups"]), 3)
        self.assertContains(response, "등록")

        week = self.client.get(reverse("discussions:list"), {"period": "7"}).context["entries"]
        self.assertEqual([x.pk for x in week], [self.deep.pk, self.child.pk])

        # 날짜로 찾기: 그날 바뀌었거나 그날 요약 이력이 있는 것
        day = timezone.localtime(now - timedelta(days=9)).date().isoformat()
        picked = self.client.get(reverse("discussions:list"), {"from": day, "to": day}).context["entries"]
        self.assertEqual([x.pk for x in picked], [self.root.pk])
        # 지난 요약 내용으로도 찾는다
        self.assertEqual([x.pk for x in self.client.get(reverse("discussions:list"), {"q": "열흘 전"}).context["entries"]], [self.root.pk])

    def test_existing_login_requirement_covers_new_menus(self):
        from django.conf import settings
        middleware = list(settings.MIDDLEWARE)
        login_middleware = "django.contrib.auth.middleware.LoginRequiredMiddleware"
        if login_middleware not in middleware:
            middleware.append(login_middleware)
        with self.settings(MIDDLEWARE=middleware):
            for url in ["/blog/", "/video/", "/discussions/"]:
                response = Client().get(url)
                self.assertEqual(response.status_code, 302)
                self.assertTrue(response["Location"].startswith("/login/?next="))
