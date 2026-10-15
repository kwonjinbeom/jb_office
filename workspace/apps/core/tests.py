import json
import tempfile
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.db import connection
from django.test import Client, TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from apps.blog_types.models import Category, PostType, Section, SubType
from apps.content.models import Content, Folder, Publication
from apps.daily_ideas.models import SearchStandard
from apps.discussions.models import Discussion, DiscussionHistory
from apps.evidence.models import Evidence
from apps.ideas.models import Idea, IdeaLog, Stage
from apps.memos.models import Memo
from apps.naver_writing.models import Post as NaverPost
from apps.tasks.models import Task
from apps.writing.models import Post

from .models import SourceExclusion, TrashEntry
from .trash import TrashError, hide_source, hidden_keys, move_to_trash, purge_expired, restore


@override_settings(TRASH_CLEANUP_ENABLED=False)
class TrashTests(TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.settings = override_settings(DISCUSSIONS_DIR=Path(self.directory.name)/"empty")
        self.settings.enable()
        self.addCleanup(self.settings.disable)
        self.git = patch("apps.core.gitstate.deploy_status", return_value=None)
        self.git.start()
        self.addCleanup(self.git.stop)

    def post_json(self, name, data):
        return self.client.post(reverse(f"core:{name}"), json.dumps(data), content_type="application/json")

    def make_tree(self):
        idea = Idea.objects.create(code="Q01", title="삭제 확인용 아이디어")
        stage = Stage.objects.create(idea=idea, title="검증 단계")
        log = IdeaLog.objects.create(idea=idea, stage=stage, body="원래 기록")
        task = Task.objects.create(idea=idea, stage=stage, title="연결된 할 일")
        evidence = Evidence.objects.create(idea=idea, stage=stage, url="https://example.com", title="확인 근거")
        return idea, stage, log, task, evidence

    def test_delete_is_a_flag_and_restore_preserves_ids_body_and_original_dates(self):
        body = "큰 본문" * 50000
        post = NaverPost.objects.create(title="원고", body=body, stage="review")
        updated = post.updated_at
        entry = move_to_trash(post)
        self.assertFalse(NaverPost.objects.filter(pk=post.pk).exists())
        retained = NaverPost.all_objects.get(pk=post.pk)
        self.assertEqual(retained.body, body)
        self.assertEqual(retained.updated_at, updated)
        self.assertLess(len(json.dumps(entry.members)), 100)
        self.assertFalse(hasattr(entry, "body"))
        restore(entry)
        live = NaverPost.objects.get(pk=post.pk)
        self.assertEqual(live.stage, "review")
        self.assertEqual(live.body, body)
        self.assertIsNone(live.deleted_at)
        self.assertEqual(live.updated_at, updated)

    def test_related_flags_restore_without_recreating_foreign_keys(self):
        objects = self.make_tree()
        entry = move_to_trash(objects[0])
        for obj in objects:
            self.assertFalse(type(obj).objects.filter(pk=obj.pk).exists())
            self.assertTrue(type(obj).all_objects.filter(pk=obj.pk, deleted_at=entry.deleted_at).exists())
        restore(entry)
        for obj in objects:
            self.assertTrue(type(obj).objects.filter(pk=obj.pk).exists())
        self.assertEqual(Task.objects.get(pk=objects[3].pk).stage_id, objects[1].pk)
        self.assertEqual(Evidence.objects.get(pk=objects[4].pk).idea_id, objects[0].pk)

    def test_independently_deleted_child_stays_deleted_when_parent_is_restored(self):
        idea, stage, log, task, evidence = self.make_tree()
        earlier = move_to_trash(stage)
        parent = move_to_trash(idea)
        restore(parent)
        self.assertTrue(Idea.objects.filter(pk=idea.pk).exists())
        self.assertFalse(Stage.objects.filter(pk=stage.pk).exists())
        restore(earlier)
        self.assertTrue(Stage.objects.filter(pk=stage.pk).exists())

    def test_double_delete_does_not_duplicate_or_extend_deadline(self):
        memo = Memo.objects.create(title="메모")
        entry = move_to_trash(memo)
        self.assertIsNone(move_to_trash(memo))
        self.assertEqual(TrashEntry.objects.count(), 1)
        self.assertEqual(TrashEntry.objects.get().deleted_at, entry.deleted_at)

    def test_queryset_and_legacy_endpoint_use_the_same_trash(self):
        first = Memo.objects.create(title="첫 메모")
        second = Memo.objects.create(title="둘째 메모")
        Memo.objects.filter(pk=first.pk).delete()
        self.client.post(reverse("memos:delete", args=[second.pk]))
        self.assertEqual(Memo.objects.count(), 0)
        self.assertEqual(Memo.all_objects.count(), 2)
        self.assertEqual(TrashEntry.objects.filter(model_label="memos.memo").count(), 2)

    def test_seven_days_boundary_and_permanent_deletion(self):
        now = timezone.now()
        expired = Memo.objects.create(title="만료")
        recent = Memo.objects.create(title="보관 중")
        with patch("apps.core.trash.timezone.now", return_value=now-timedelta(days=7)):
            entry = move_to_trash(expired)
        with patch("apps.core.trash.timezone.now", return_value=now-timedelta(days=7)+timedelta(seconds=1)):
            move_to_trash(recent)
        self.assertEqual(purge_expired(now=now), 1)
        self.assertFalse(Memo.all_objects.filter(pk=expired.pk).exists())
        self.assertTrue(Memo.all_objects.filter(pk=recent.pk).exists())
        self.assertFalse(TrashEntry.objects.filter(pk=entry.pk).exists())

    def test_expired_item_cannot_be_restored_before_cleanup(self):
        memo = Memo.objects.create(title="만료")
        with patch("apps.core.trash.timezone.now", return_value=timezone.now()-timedelta(days=8)):
            entry = move_to_trash(memo)
        with self.assertRaisesMessage(TrashError, "7일"):
            restore(entry)
        self.assertFalse(Memo.objects.filter(pk=memo.pk).exists())

    def test_protected_folder_tree_can_be_purged_without_deleting_other_folders(self):
        root = Folder.objects.create(workspace="blog", name="상위")
        child = Folder.objects.create(workspace="blog", name="하위", parent=root)
        content = Content.objects.create(workspace="blog", folder=child, title="글")
        publication = Publication.objects.create(content=content, channel="게시처")
        keep = Folder.objects.create(workspace="blog", name="유지")
        with patch("apps.core.trash.timezone.now", return_value=timezone.now()-timedelta(days=8)):
            move_to_trash(root)
        self.assertEqual(purge_expired(), 1)
        for obj in [root, child, content, publication]:
            self.assertFalse(type(obj).all_objects.filter(pk=obj.pk).exists())
        self.assertTrue(Folder.objects.filter(pk=keep.pk).exists())

    def test_cleanup_never_cascades_through_new_live_children(self):
        root = Folder.objects.create(workspace="blog", name="상위")
        with patch("apps.core.trash.timezone.now", return_value=timezone.now()-timedelta(days=8)):
            move_to_trash(root)
        child = Folder.objects.create(workspace="blog", parent=root, name="보호할 하위")
        self.assertEqual(purge_expired(), 0)
        self.assertTrue(Folder.objects.filter(pk=child.pk).exists())

    def test_source_exclusion_survives_expiry_but_keeps_git_file(self):
        source = Path(self.directory.name)/"자료.md"
        source.write_text("# 원본 자료", encoding="utf-8")
        with override_settings(REPO_ROOT=Path(self.directory.name), DOCS_DIRS=[Path(self.directory.name)]):
            response = self.post_json("trash_move", {"items": [{"model": "source.docs", "id": "자료.md"}]})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(self.client.get(reverse("docs:detail", args=["자료.md"])).status_code, 404)
            self.assertTrue(source.exists())
            self.assertNotContains(self.client.get(reverse("docs:list")), 'data-trash-id="자료.md"')
            restore(TrashEntry.objects.get(model_label="source.docs"))
            self.assertEqual(self.client.get(reverse("docs:detail", args=["자료.md"])).status_code, 200)
            with patch("apps.core.trash.timezone.now", return_value=timezone.now()-timedelta(days=8)):
                hide_source("docs", "자료.md", "자료")
            purge_expired()
            self.assertIn("자료.md", hidden_keys("docs"))
            self.assertTrue(source.exists())
            self.assertEqual(TrashEntry.objects.count(), 0)

    def test_daily_item_stays_hidden_after_reload_and_restores(self):
        from apps.daily_ideas.data import load_batches
        batches = load_batches()
        item = batches[0]["items"][0]
        entry = hide_source("daily", item["id"], item["title"])
        response = self.client.get(reverse("daily_ideas:list"), {"date": "all"})
        self.assertNotContains(response, f'data-trash-id="{item["id"]}"')
        self.assertEqual(self.client.post(reverse("daily_ideas:adopt", args=[item["id"]])).status_code, 404)
        restore(entry)
        self.assertContains(self.client.get(reverse("daily_ideas:list"), {"date": "all"}), f'data-trash-id="{item["id"]}"')

    def test_deleted_discussion_source_is_not_reimported_after_expiry(self):
        from apps.discussions import docs
        folder = Path(self.directory.name)/"논의"
        folder.mkdir()
        (folder/"대화.md").write_text("---\n대구분: 블로그·카페\n제목: 삭제할 논의\n---\n\n# 내용", encoding="utf-8")
        with override_settings(REPO_ROOT=Path(self.directory.name), DISCUSSIONS_DIR=folder):
            docs.sync()
            obj = Discussion.objects.get(doc="논의/대화.md")
            with patch("apps.core.trash.timezone.now", return_value=timezone.now()-timedelta(days=8)):
                move_to_trash(obj)
            docs.sync()
            self.assertFalse(Discussion.objects.filter(doc=obj.doc).exists())
            purge_expired()
            docs.sync()
            self.assertFalse(Discussion.all_objects.filter(doc=obj.doc).exists())
            self.assertTrue((folder/"대화.md").exists())

    def test_preview_is_read_only_and_deduplicates_connected_selection(self):
        idea, stage, *_ = self.make_tree()
        response = self.post_json("trash_preview", {"items": [{"model":"ideas.idea", "id":idea.pk}, {"model":"ideas.stage", "id":stage.pk}]})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 5)
        self.assertEqual(TrashEntry.objects.count(), 0)
        self.assertEqual(Idea.objects.count(), 1)

    def test_bulk_invalid_target_rolls_back_all_changes(self):
        memo = Memo.objects.create(title="유지")
        response = self.post_json("trash_move", {"items":[{"model":"memos.memo", "id":memo.pk},{"model":"auth.user", "id":1}]})
        self.assertEqual(response.status_code, 400)
        self.assertTrue(Memo.objects.filter(pk=memo.pk).exists())
        self.assertEqual(TrashEntry.objects.count(), 0)

    def test_post_only_csrf_and_payload_validation(self):
        for route in ["trash_move", "trash_restore", "trash_preview"]:
            self.assertEqual(self.client.get(reverse(f"core:{route}")).status_code, 405)
        self.assertEqual(Client(enforce_csrf_checks=True).post(reverse("core:trash_move"), "{}", content_type="application/json").status_code, 403)
        for data in [[], {}, {"items":[]}, {"items": "bad"}, {"items":[{}]}, {"items":[{"model":"memos.memo","id":"../1"}]}]:
            self.assertEqual(self.post_json("trash_move", data).status_code, 400)

    def test_multiple_restore_can_include_independently_trashed_parent(self):
        idea, stage, *_ = self.make_tree()
        child_entry = move_to_trash(stage)
        root_entry = move_to_trash(idea)
        response = self.post_json("trash_restore", {"ids":[child_entry.pk, root_entry.pk]})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Stage.objects.filter(pk=stage.pk).exists())

    def test_unique_codes_are_reserved_until_permanent_deletion(self):
        idea = Idea.objects.create(code="C01", title="기존")
        move_to_trash(idea)
        with self.assertRaises(ValidationError):
            Idea(code="C01", title="중복").full_clean()
        from apps.daily_ideas.views import _next_code
        self.assertEqual(_next_code(), "C02")

    def test_standard_version_does_not_reuse_hidden_versions(self):
        first = SearchStandard.objects.create(version=1, goal="첫 버전")
        second = SearchStandard.objects.create(version=2, goal="둘째 버전")
        move_to_trash(second)
        self.client.post(reverse("daily_ideas:standard"), {"goal":"새 내용"})
        self.assertTrue(SearchStandard.objects.filter(version=3).exists())

    def test_trash_listing_is_paginated_and_does_not_load_original_bodies(self):
        for n in range(55):
            move_to_trash(NaverPost.objects.create(title=f"원고 {n}", body="비싼 본문"*1000))
        with CaptureQueriesContext(connection) as queries:
            response = self.client.get(reverse("core:trash"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["page"]), 50)
        self.assertFalse(any('FROM "naver_writing_post"' in q["sql"] for q in queries))
        self.assertContains(response, "다음")
        self.assertEqual(len(self.client.get(reverse("core:trash"), {"page":2}).context["page"]), 5)

    def test_all_user_data_grids_have_common_controls(self):
        idea, stage, log, task, evidence = self.make_tree()
        Memo.objects.create(title="메모")
        Folder.objects.create(workspace="blog", name="폴더")
        content = Content.objects.create(workspace="blog", title="콘텐츠")
        Publication.objects.create(content=content, channel="채널")
        discussion = Discussion.objects.create(name="논의", area="blog")
        DiscussionHistory.objects.create(discussion=discussion, status="new", amount="none", partner="none")
        SearchStandard.objects.create(version=1)
        Post.objects.create(title="티스토리")
        NaverPost.objects.create(title="네이버")
        category = Category.objects.create(section=Section.objects.first(), code="Z", name="카테고리")
        post_type = PostType.objects.create(category=category, name="타입")
        SubType.objects.create(post_type=post_type, name="하위")
        paths = ["/", "/ideas/", f"/ideas/{idea.pk}/", "/memos/", "/blog/", "/video/", "/blog/writing/", "/blog/writing/review/", "/blog/writing/posts/", "/blog/naver-writing/", "/blog/naver-writing/review/", "/blog/naver-writing/posts/", "/blog/types/", "/daily-ideas/", "/daily-ideas/standard/", "/discussions/", f"/discussions/{discussion.pk}/", "/tasks/", "/evidence/", "/docs/", "/trash/"]
        for path in paths:
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, 'id="trash-dialog"')
        for route,label in [("ideas:list","ideas.idea"),("memos:list","memos.memo"),("writing:list","writing.post"),("naver_writing:list","naver_writing.post"),("blog:list","content.content"),("tasks:list","tasks.task"),("evidence:list","evidence.evidence"),("blog_types:index","blog_types.category")]:
            with self.subTest(route=route):
                self.assertContains(self.client.get(reverse(route)), f'data-trash-model="{label}"')

    def test_section_flags_all_four_levels_and_restores_same_rows(self):
        section = Section.objects.create(name="새 대분류")
        category = Category.objects.create(section=section, code="A", name="카테고리")
        post_type = PostType.objects.create(category=category, name="타입")
        sub = SubType.objects.create(post_type=post_type, name="하위")
        entry = move_to_trash(section)
        self.assertEqual(entry.item_count, 4)
        for obj in (section, category, post_type, sub):
            self.assertFalse(type(obj).objects.filter(pk=obj.pk).exists())
            self.assertTrue(type(obj).all_objects.filter(pk=obj.pk).exists())
        restore(entry)
        sub.refresh_from_db()
        self.assertEqual(sub.post_type.category.section_id, section.pk)
        self.assertIsNone(sub.deleted_at)

    @override_settings(REQUIRE_LOGIN=True)
    def test_server_authentication_covers_trash_api(self):
        from django.contrib.auth.middleware import LoginRequiredMiddleware
        from django.http import HttpResponse
        from django.test import RequestFactory
        from django.contrib.auth.models import AnonymousUser
        request = RequestFactory().post("/trash/move/")
        request.user = AnonymousUser()
        result = LoginRequiredMiddleware(lambda r: HttpResponse()).process_view(request, __import__("apps.core.trash_views",fromlist=["move"]).move, (), {})
        self.assertEqual(result.status_code, 302)
