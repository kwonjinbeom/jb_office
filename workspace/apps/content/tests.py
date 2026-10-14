from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from django.urls import reverse

from .forms import ContentForm, FolderForm
from .models import Content, Folder, Publication


@override_settings(REQUIRE_LOGIN=False)
class ContentTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.root = Folder.objects.create(workspace="blog", name="블로그")
        cls.child = Folder.objects.create(workspace="blog", name="제품 비교", parent=cls.root)
        cls.deep = Folder.objects.create(workspace="blog", name="AI 도구", parent=cls.child)
        cls.video = Folder.objects.create(workspace="video", name="이야기")
        cls.template = Content.objects.create(workspace="blog", folder=cls.deep, title="비교 템플릿", kind="template", body="비교 기준\n근거와 결론", outline="대상 독자", scenes="공식 출처")
        cls.work = Content.objects.create(workspace="video", folder=cls.video, title="첫 영상", body="도입부")
        cls.publication = Publication.objects.create(content=cls.work, channel="TikTok", version="짧은 도입부")

    def setUp(self):
        # 화면 렌더링 중 원격 배포 상태 조회를 실행하지 않는다.
        self.patcher = patch("apps.core.context_processors.gitstate.deploy_status", return_value=None)
        self.patcher.start()
        self.addCleanup(self.patcher.stop)

    def test_folder_cycle_and_cross_workspace_are_rejected(self):
        self.root.parent = self.deep
        with self.assertRaises(ValidationError):
            self.root.full_clean()
        self.root.parent = self.video
        with self.assertRaises(ValidationError):
            self.root.full_clean()
        form = FolderForm({"name": "블로그", "parent": self.deep.pk}, workspace="blog", instance=self.root)
        self.assertFalse(form.is_valid())

    def test_content_cannot_use_other_workspace_folder(self):
        form = ContentForm({"title": "새 글", "folder": self.video.pk, "kind": "work", "status": "draft"}, workspace="blog")
        self.assertFalse(form.is_valid())
        self.assertIn("folder", form.errors)

    def test_parent_folder_filter_includes_deep_descendants(self):
        response = self.client.get(reverse("blog:list"), {"folder": self.root.pk})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "비교 템플릿")
        self.assertNotContains(response, "첫 영상")
        self.assertContains(response, "블로그 / 제품 비교 / AI 도구")
        self.assertEqual(self.client.get(reverse("blog:list"), {"q": "없는 제목"}).context["entries"], [])

    def test_template_starts_new_work_without_modifying_original(self):
        response = self.client.get(reverse("blog:create"), {"template": self.template.pk})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["form"].initial["body"], self.template.body)
        self.assertEqual(response.context["form"].initial["kind"], "work")
        response = self.client.post(reverse("blog:create"), {"title": "실제 비교글", "folder": self.deep.pk, "kind": "work", "status": "draft", "body": "새 원고"})
        self.assertEqual(response.status_code, 302)
        self.template.refresh_from_db()
        self.assertEqual(self.template.body, "비교 기준\n근거와 결론")
        self.assertTrue(Content.objects.filter(title="실제 비교글", workspace="blog").exists())

    def test_all_content_screens_render_and_cross_menu_ids_are_hidden(self):
        for space, item, folder in [("blog", self.template, self.root), ("video", self.work, self.video)]:
            for name, args in [("list", []), ("create", []), ("folder_create", []), ("detail", [item.pk]), ("edit", [item.pk]), ("delete", [item.pk]), ("folder_edit", [folder.pk]), ("folder_delete", [folder.pk]), ("publication_create", [item.pk])]:
                with self.subTest(space=space, name=name):
                    self.assertEqual(self.client.get(reverse(f"{space}:{name}", args=args)).status_code, 200)
        for name in ["publication_edit", "publication_delete"]:
            self.assertEqual(self.client.get(reverse(f"video:{name}", args=[self.work.pk, self.publication.pk])).status_code, 200)
        self.assertEqual(self.client.get(reverse("blog:detail", args=[self.work.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse("blog:create"), {"template": self.work.pk}).status_code, 404)

    def test_delete_protects_folder_and_get_never_changes_status(self):
        self.assertEqual(self.client.get(reverse("blog:status", args=[self.template.pk])).status_code, 405)
        self.client.post(reverse("blog:folder_delete", args=[self.root.pk]))
        self.assertTrue(Folder.objects.filter(pk=self.root.pk).exists())
        self.client.post(reverse("blog:status", args=[self.template.pk]), {"status": "invalid"})
        self.template.refresh_from_db()
        self.assertEqual(self.template.status, "topic")
        self.client.post(reverse("blog:status", args=[self.template.pk]), {"status": "ready"})
        self.template.refresh_from_db()
        self.assertEqual(self.template.status, "ready")

    def test_publication_create_edit_delete_and_safe_url_validation(self):
        url = reverse("video:publication_create", args=[self.work.pk])
        response = self.client.post(url, {"channel": "YouTube Shorts", "url": "javascript:alert(1)"})
        self.assertEqual(response.status_code, 200)
        self.assertIn("url", response.context["form"].errors)
        response = self.client.post(url, {"channel": "YouTube Shorts", "url": "https://youtube.com/watch?v=test", "published_on": "2026-10-14", "result": "첫 반응 확인"})
        self.assertEqual(response.status_code, 302)
        publication = self.work.publications.get(channel="YouTube Shorts")
        self.client.post(reverse("video:publication_edit", args=[self.work.pk, publication.pk]), {"channel": "YouTube Shorts", "result": "도입부 수정"})
        publication.refresh_from_db()
        self.assertEqual(publication.result, "도입부 수정")
        self.client.post(reverse("video:publication_delete", args=[self.work.pk, publication.pk]))
        self.assertFalse(Publication.objects.filter(pk=publication.pk).exists())

    def test_download_contains_original_and_platform_version(self):
        response = self.client.get(reverse("video:download", args=[self.work.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "# 첫 영상")
        self.assertContains(response, "TikTok")
        self.assertContains(response, "짧은 도입부")
        self.assertIn("attachment", response["Content-Disposition"])
        self.assertEqual(self.client.get(reverse("blog:download", args=[self.work.pk])).status_code, 404)

    def test_status_preserves_filters_without_external_redirects(self):
        url = reverse("blog:status", args=[self.template.pk])
        response = self.client.post(url, {"status": "draft", "return_to": f"/blog/?folder={self.root.pk}&kind=template"})
        self.assertEqual(response["Location"], f"/blog/?folder={self.root.pk}&kind=template")
        for target in ["https://example.com/blog/", "//example.com/blog/", "http://[", "/settings/"]:
            response = self.client.post(url, {"status": "draft", "return_to": target})
            self.assertEqual(response["Location"], "/blog/")
