import json
from io import BytesIO
from unittest.mock import patch
from urllib.error import HTTPError

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from apps.content.models import Content, Folder, Publication
from apps.core.models import AppSetting
from . import ai, services
from .catalog import MANUAL_CHECKS
from .models import Draft, DraftRevision, WritingProfile, WritingTemplate


@override_settings(REQUIRE_LOGIN=False)
class WritingTests(TestCase):
    def setUp(self):
        patcher = patch(
            "apps.core.context_processors.gitstate.deploy_status", return_value=None
        )
        patcher.start()
        self.addCleanup(patcher.stop)
        self.profile = WritingProfile.objects.create(
            name="도구 비교",
            audience="처음 고르는 사람",
            blog_url="https://example.tistory.com",
            disclosure="이 글에는 제휴 링크가 포함되어 있습니다.",
        )
        self.folder = Folder.objects.create(workspace="blog", name="비교 글")
        self.content = Content.objects.create(
            workspace="blog",
            kind="work",
            status="draft",
            title="다이어리 선택",
            body="## 선택 기준\n\n사용 목적을 확인하세요.",
            folder=self.folder,
        )
        self.draft = Draft.objects.create(
            content=self.content,
            profile=self.profile,
            template_key="compare",
            keyword="다이어리",
            question="기록용과 일정용의 차이는?",
            answer="기록하는 목적에 맞춰 고릅니다.",
        )

    def data(self, **changes):
        self.draft.refresh_from_db()
        self.content.refresh_from_db()
        result = {
            "title": self.content.title,
            "body": self.content.body,
            "status": self.content.status,
            "folder": self.folder.pk,
            "profile": self.draft.profile_id or "",
            "template_key": self.draft.template_key,
            "keyword": self.draft.keyword,
            "tags": self.draft.tags,
            "question": self.draft.question,
            "answer": self.draft.answer,
            "experience": self.draft.experience,
            "description": self.draft.description,
            "sources": json.dumps(self.draft.sources),
            "checks": self.draft.checks,
            "revision": self.draft.revision,
            "signature": services.signature(self.content),
            "published_url": self.draft.published_url,
            "published_on": self.draft.published_on.isoformat()
            if self.draft.published_on
            else "",
        }
        if self.draft.commercial:
            result["commercial"] = "on"
        result.update(changes)
        return result

    def token(self, **changes):
        data = self.data()
        return {"revision": data["revision"], "signature": data["signature"], **changes}

    def test_create_and_all_screens_render_with_blog_navigation(self):
        for name, args in [
            ("list", []),
            ("create", []),
            ("templates", []),
            ("template_create", []),
            ("settings", []),
            ("profile_create", []),
            ("profile_edit", [self.profile.pk]),
            ("editor", [self.draft.pk]),
            ("delete", [self.draft.pk]),
        ]:
            response = self.client.get(reverse(f"writing:{name}", args=args))
            self.assertEqual(response.status_code, 200, name)
            self.assertContains(response, "티스토리 글쓰기")
        response = self.client.post(
            reverse("writing:create"),
            {
                "title": "새 경험 글",
                "template_key": "experience",
                "profile": self.profile.pk,
                "folder": self.folder.pk,
            },
        )
        self.assertEqual(response.status_code, 302)
        created = Draft.objects.get(content__title="새 경험 글")
        self.assertEqual(created.content.workspace, "blog")
        self.assertEqual(created.content.kind, "work")

    def test_save_updates_shared_content_and_keeps_prior_version(self):
        response = self.client.post(
            reverse("writing:save", args=[self.draft.pk]),
            self.data(
                title="새 제목",
                body="## 새 본문\n\n검토한 결과입니다.",
                tags=" 기록, #다이어리, 기록 ",
            ),
        )
        self.assertEqual(response.status_code, 200)
        self.content.refresh_from_db()
        self.draft.refresh_from_db()
        self.assertEqual(self.content.title, "새 제목")
        self.assertEqual(self.draft.tags, "기록, 다이어리")
        self.assertEqual(self.draft.revision, 2)
        self.assertEqual(
            self.draft.versions.first().payload["content"]["title"], "다이어리 선택"
        )
        response = self.client.post(
            reverse("writing:save", args=[self.draft.pk]), self.data()
        )
        self.assertEqual(response.status_code, 200)
        self.draft.refresh_from_db()
        self.assertEqual(self.draft.revision, 2)

    def test_stale_writer_and_changes_in_generic_editor_are_rejected(self):
        stale = self.data()
        self.client.post(
            reverse("writing:save", args=[self.draft.pk]), self.data(body="첫 창 변경")
        )
        response = self.client.post(
            reverse("writing:save", args=[self.draft.pk]), stale
        )
        self.assertEqual(response.status_code, 409)
        current = self.data()
        self.content.title = "콘텐츠 메뉴에서 바꾼 제목"
        self.content.save()
        response = self.client.post(
            reverse("writing:save", args=[self.draft.pk]), current
        )
        self.assertEqual(response.status_code, 409)
        self.content.refresh_from_db()
        self.assertEqual(self.content.title, "콘텐츠 메뉴에서 바꾼 제목")

    def test_sources_and_tags_validate_without_partial_save(self):
        invalid_sources = [
            [{"title": "자료", "url": "javascript:alert(1)"}],
            [{"title": "자료", "checked_on": "2026-88-01"}],
            "not a list",
            [{"title": "x"}] * 31,
        ]
        for sources in invalid_sources:
            response = self.client.post(
                reverse("writing:save", args=[self.draft.pk]),
                self.data(title="바뀌면 안 되는 제목", sources=json.dumps(sources)),
            )
            self.assertEqual(response.status_code, 400)
        response = self.client.post(
            reverse("writing:save", args=[self.draft.pk]),
            self.data(tags=",".join(str(n) for n in range(11))),
        )
        self.assertEqual(response.status_code, 400)
        self.content.refresh_from_db()
        self.assertEqual(self.content.title, "다이어리 선택")

    def test_preview_does_not_save_and_export_filters_executable_html(self):
        malicious = '## 소제목\n\n<script>alert(1)</script><img src="https://example.com/x.png" onerror="alert(1)"><a href="javascript:alert(1)">링크</a><a href="https://[">깨진 주소</a>'
        response = self.client.post(
            reverse("writing:preview", args=[self.draft.pk]), self.data(body=malicious)
        )
        self.assertEqual(response.status_code, 200)
        rendered = response.json()["html"]
        self.assertNotIn("<script", rendered)
        self.assertNotIn("onerror", rendered)
        self.assertNotIn("javascript:", rendered)
        self.assertIn('data-ke-size="size26"', rendered)
        self.content.refresh_from_db()
        self.assertNotIn("script", self.content.body)

    def test_checked_sources_and_real_disclosure_are_added_to_exports(self):
        self.draft.sources = [
            {
                "title": "공식 자료",
                "url": "https://example.com/docs",
                "note": "확인한 사실",
                "verified": True,
                "checked_on": "2026-10-14",
            },
            {"title": "미확인", "url": "https://example.com/unread", "verified": False},
        ]
        self.draft.commercial = True
        self.draft.save()
        response = self.client.get(
            reverse("writing:download", args=[self.draft.pk, "html"])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.profile.disclosure)
        self.assertContains(response, "https://example.com/docs")
        self.assertNotContains(response, "https://example.com/unread")
        for kind in ["md", "json"]:
            response = self.client.get(
                reverse("writing:download", args=[self.draft.pk, kind])
            )
            self.assertEqual(response.status_code, 200)
            self.assertIn("attachment", response["Content-Disposition"])

    def test_scaffold_restore_and_version_retention(self):
        original = self.content.body
        response = self.client.post(
            reverse("writing:action", args=[self.draft.pk]),
            self.token(action="scaffold"),
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("[[", response.json()["values"]["body"])
        self.assertIn(self.draft.answer, response.json()["values"]["body"])
        version = self.draft.versions.first()
        response = self.client.post(
            reverse("writing:action", args=[self.draft.pk]),
            self.token(action="restore", version=version.pk),
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["values"]["body"], original)
        for _ in range(35):
            services.remember(self.draft, "테스트 버전")
        self.assertEqual(self.draft.versions.count(), 30)

    def test_manual_checks_reset_on_body_and_evidence_changes(self):
        keys = [key for key, _ in MANUAL_CHECKS]
        response = self.client.post(
            reverse("writing:save", args=[self.draft.pk]), self.data(checks=keys)
        )
        self.assertEqual(response.json()["values"]["checks"], keys)
        response = self.client.post(
            reverse("writing:save", args=[self.draft.pk]),
            self.data(body="본문 변경", checks=keys),
        )
        self.assertEqual(response.json()["values"]["checks"], [])
        self.client.post(
            reverse("writing:save", args=[self.draft.pk]), self.data(checks=keys)
        )
        response = self.client.post(
            reverse("writing:save", args=[self.draft.pk]),
            self.data(experience="직접 테스트 내용 추가", checks=keys),
        )
        self.assertEqual(response.json()["values"]["checks"], [])

    def test_publication_and_duplicate_connect_to_existing_content(self):
        response = self.client.post(
            reverse("writing:save", args=[self.draft.pk]),
            self.data(
                status="published",
                published_url="https://example.tistory.com/1",
                published_on="2026-10-14",
            ),
        )
        self.assertEqual(response.status_code, 200)
        publication = Publication.objects.get(content=self.content, channel="티스토리")
        self.assertEqual(publication.url, "https://example.tistory.com/1")
        response = self.client.post(reverse("writing:duplicate", args=[self.draft.pk]))
        self.assertEqual(response.status_code, 302)
        copy = Draft.objects.exclude(pk=self.draft.pk).get()
        self.assertEqual(copy.content.status, "draft")
        self.assertEqual(copy.published_url, "")

    def test_existing_content_can_be_attached_once_but_video_cannot(self):
        content = Content.objects.create(
            workspace="blog", kind="work", title="기존 글", body="기존 본문"
        )
        for _ in range(2):
            self.assertEqual(
                self.client.post(
                    reverse("writing:attach", args=[content.pk])
                ).status_code,
                302,
            )
        self.assertEqual(Draft.objects.filter(content=content).count(), 1)
        video = Content.objects.create(workspace="video", kind="work", title="영상")
        self.assertEqual(
            self.client.post(reverse("writing:attach", args=[video.pk])).status_code,
            404,
        )

    def test_custom_template_and_profile_used_by_prompt_without_fake_experience(self):
        custom = WritingTemplate.objects.create(
            name="내 글", body="{{answer}}\n\n## 실제 경험\n{{experience}}"
        )
        self.draft.template_key = f"custom:{custom.pk}"
        self.draft.save()
        self.assertIn(self.draft.answer, services.scaffold(self.draft))
        self.assertIn("제공된 직접 경험 없음", services.prompt(self.draft))
        self.assertIn(self.profile.audience, services.prompt(self.draft))
        custom.delete()
        self.assertEqual(services.template(self.draft)["key"], "howto")
        self.assertEqual(
            self.client.get(self.draft.get_absolute_url()).status_code, 200
        )

    def test_ai_settings_never_return_stored_key_and_do_not_block_other_tools(self):
        response = self.client.post(
            reverse("writing:settings"),
            {"api_key": "test-key-do-not-display", "model": "gpt-4.1-mini"},
        )
        self.assertEqual(response.status_code, 302)
        for path in [
            reverse("writing:settings"),
            self.draft.get_absolute_url(),
            reverse("writing:download", args=[self.draft.pk, "json"]),
        ]:
            response = self.client.get(path)
            self.assertNotContains(response, "test-key-do-not-display")
        self.client.post(
            reverse("writing:settings"), {"model": "gpt-4.1-mini", "remove_key": "on"}
        )
        self.assertEqual(AppSetting.get(ai.KEY_SETTING), "")

    @patch("apps.writing.views.ai.generate")
    def test_ai_generation_saves_version_and_conflict_preserves_new_edits(
        self, generate
    ):
        generate.return_value = {
            "title": "AI 제안 제목",
            "body": "## 제안 초안\n\n자료를 확인하세요.",
            "description": "소개",
            "tags": "기록",
        }
        response = self.client.post(
            reverse("writing:action", args=[self.draft.pk]), self.token(action="ai")
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            self.draft.versions.first().payload["content"]["title"], "다이어리 선택"
        )

        def concurrent(draft):
            Content.objects.filter(pk=draft.content_id).update(
                body="다른 창에서 작성한 본문"
            )
            return {"title": "제안", "body": "생성 결과", "description": "", "tags": ""}

        generate.side_effect = concurrent
        response = self.client.post(
            reverse("writing:action", args=[self.draft.pk]), self.token(action="ai")
        )
        self.assertEqual(response.status_code, 409)
        self.assertIn("generated", response.json())
        self.content.refresh_from_db()
        self.assertEqual(self.content.body, "다른 창에서 작성한 본문")

    def test_ai_provider_errors_do_not_expose_keys_or_modify_draft(self):
        with (
            patch(
                "apps.writing.ai.configuration",
                return_value=("private-secret-key", "gpt-4.1-mini"),
            ),
            patch(
                "urllib.request.urlopen",
                side_effect=HTTPError(
                    "https://api.openai.com", 401, "private-secret-key", {}, None
                ),
            ),
        ):
            response = self.client.post(
                reverse("writing:action", args=[self.draft.pk]), self.token(action="ai")
            )
        self.assertEqual(response.status_code, 400)
        self.assertNotContains(response, "private-secret-key", status_code=400)
        self.content.refresh_from_db()
        self.assertEqual(self.content.title, "다이어리 선택")

    def test_mutations_require_post_csrf_and_site_login(self):
        for name in ["save", "action", "duplicate"]:
            self.assertEqual(
                self.client.get(
                    reverse(f"writing:{name}", args=[self.draft.pk])
                ).status_code,
                405,
            )
        self.assertEqual(
            Client(enforce_csrf_checks=True)
            .post(reverse("writing:save", args=[self.draft.pk]), self.data())
            .status_code,
            403,
        )
        middleware = list(settings.MIDDLEWARE)
        if "django.contrib.auth.middleware.LoginRequiredMiddleware" not in middleware:
            middleware.append("django.contrib.auth.middleware.LoginRequiredMiddleware")
        with self.settings(MIDDLEWARE=middleware):
            response = Client().get(reverse("writing:list"))
            self.assertEqual(response.status_code, 302)
            self.assertTrue(response["Location"].startswith("/login/"))

    def test_backup_round_trip_and_invalid_import_never_create_partial_content(self):
        backup = services.snapshot(self.draft)
        backup["draft"]["published_url"] = "https://example.tistory.com/1"
        backup["content"]["status"] = "published"
        file = SimpleUploadedFile(
            "backup.json", json.dumps(backup).encode(), content_type="application/json"
        )
        response = self.client.post(reverse("writing:import"), {"file": file})
        self.assertEqual(response.status_code, 302)
        created = Draft.objects.exclude(pk=self.draft.pk).get()
        self.assertEqual(created.content.body, self.content.body)
        self.assertEqual(created.content.status, "draft")
        self.assertEqual(created.published_url, "")
        count = Content.objects.count()
        for bad in [b"not json", b"[]", b'{"content":{},"draft":{}}']:
            response = self.client.post(
                reverse("writing:import"), {"file": SimpleUploadedFile("bad.json", bad)}
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(Content.objects.count(), count)

    def test_deleting_profile_or_template_preserves_original_draft_body(self):
        custom = WritingTemplate.objects.create(name="사용자 틀", body="{{answer}}")
        self.draft.template_key = f"custom:{custom.pk}"
        self.draft.save()
        self.assertEqual(
            self.client.get(
                reverse("writing:template_delete", args=[custom.pk])
            ).status_code,
            200,
        )
        self.client.post(reverse("writing:template_delete", args=[custom.pk]))
        self.client.post(reverse("writing:profile_delete", args=[self.profile.pk]))
        self.draft.refresh_from_db()
        self.content.refresh_from_db()
        self.assertIsNone(self.draft.profile)
        self.assertEqual(self.content.body, "## 선택 기준\n\n사용 목적을 확인하세요.")
        self.assertEqual(
            self.client.get(self.draft.get_absolute_url()).status_code, 200
        )

    def test_ai_response_is_parsed_without_requesting_external_service(self):
        message = json.dumps(
            {
                "title": "새 제목",
                "body_markdown": "## 초안\n\n[[가격 확인]]",
                "description": "간단 소개",
                "tags": ["기록"],
            }
        )
        response = BytesIO(
            json.dumps({"choices": [{"message": {"content": message}}]}).encode()
        )
        with (
            patch(
                "apps.writing.ai.configuration",
                return_value=("test-key", "gpt-4.1-mini"),
            ),
            patch("urllib.request.urlopen", return_value=response) as mocked,
        ):
            result = ai.generate(self.draft)
        self.assertEqual(result["body"], "## 초안\n\n[[가격 확인]]")
        self.assertEqual(
            mocked.call_args.args[0].full_url,
            "https://api.openai.com/v1/chat/completions",
        )

    def test_restoring_after_profile_deleted_and_foreign_revision_blocked(self):
        services.remember(self.draft, "첫 버전")
        version = self.draft.versions.first()
        self.profile.delete()
        response = self.client.post(
            reverse("writing:action", args=[self.draft.pk]),
            self.token(action="restore", version=version.pk),
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["values"]["profile"], "")
        other = Draft.objects.create(
            content=Content.objects.create(
                workspace="blog", kind="work", title="다른 원고"
            )
        )
        foreign = DraftRevision.objects.create(
            draft=other, label="다른 원고 버전", payload=services.snapshot(other)
        )
        response = self.client.post(
            reverse("writing:action", args=[self.draft.pk]),
            self.token(action="restore", version=foreign.pk),
        )
        self.assertEqual(response.status_code, 404)

    def test_published_article_edit_requires_review_and_preserves_published_title(self):
        self.client.post(
            reverse("writing:save", args=[self.draft.pk]),
            self.data(
                status="published",
                published_url="https://example.tistory.com/1",
                published_on="2026-10-14",
            ),
        )
        response = self.client.post(
            reverse("writing:save", args=[self.draft.pk]),
            self.data(
                title="수정 중인 새 제목", body="새 본문\r\n\r\n다시 검토해야 합니다."
            ),
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["values"]["status"], "review")
        self.assertNotIn("\r", response.json()["values"]["body"])
        self.assertEqual(
            Publication.objects.get(content=self.content, channel="티스토리").title,
            "다이어리 선택",
        )
