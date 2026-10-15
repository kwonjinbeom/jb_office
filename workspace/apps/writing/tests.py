from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Post

Stage = Post.Stage


class PostPipelineTests(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_user("tester", password="pw-test-1234")
        self.client.force_login(user)

    def test_three_screens_open(self):
        Post.objects.create(title="임시 글", stage=Stage.TEMP)
        Post.objects.create(title="검토 글", stage=Stage.REVIEW)
        Post.objects.create(title="포스트 글", stage=Stage.POST)
        for name, title, others in [
            ("writing:list", "임시 글", ["검토 글", "포스트 글"]),
            ("writing:review", "검토 글", ["임시 글", "포스트 글"]),
            ("writing:posts", "포스트 글", ["임시 글", "검토 글"]),
        ]:
            res = self.client.get(reverse(name))
            self.assertEqual(res.status_code, 200)
            self.assertContains(res, title)
            for other in others:
                self.assertNotContains(res, other)
        res = self.client.get(reverse("writing:posts"))
        self.assertContains(res, "미작성")
        self.assertContains(res, "미발행")

    def test_create_goes_to_requested_screen(self):
        self.client.post(reverse("writing:create"), {"stage": "temp", "title": "새 템플릿", "summary": "요약"})
        self.assertEqual(Post.objects.get(title="새 템플릿").stage, Stage.TEMP)
        self.client.post(reverse("writing:create"), {"stage": "post", "title": "새 포스트",
                                                     "write_status": "todo", "publish_status": "todo"})
        self.assertEqual(Post.objects.get(title="새 포스트").stage, Stage.POST)

    def test_move_one_step_each_way(self):
        post = Post.objects.create(title="글")
        self.client.post(reverse("writing:move"), {"pk": post.pk, "to": "review"})
        post.refresh_from_db()
        self.assertEqual(post.stage, Stage.REVIEW)
        self.client.post(reverse("writing:move"), {"pk": post.pk, "to": "post"})
        post.refresh_from_db()
        self.assertEqual(post.stage, Stage.POST)
        self.client.post(reverse("writing:move"), {"pk": post.pk, "to": "review"})
        post.refresh_from_db()
        self.assertEqual(post.stage, Stage.REVIEW)

    def test_cannot_skip_a_screen(self):
        post = Post.objects.create(title="글")
        self.client.post(reverse("writing:move"), {"pk": post.pk, "to": "post"})
        post.refresh_from_db()
        self.assertEqual(post.stage, Stage.TEMP)

    def test_bulk_move(self):
        a = Post.objects.create(title="가")
        b = Post.objects.create(title="나")
        self.client.post(reverse("writing:move"), {"ids": [a.pk, b.pk], "to": "review"})
        self.assertEqual(Post.objects.filter(stage=Stage.REVIEW).count(), 2)

    def test_published_post_stays(self):
        post = Post.objects.create(title="글", stage=Stage.POST, publish_status=Post.Publish.DONE)
        self.client.post(reverse("writing:move"), {"pk": post.pk, "to": "review"})
        post.refresh_from_db()
        self.assertEqual(post.stage, Stage.POST)

    def test_status_keeps_when_moving(self):
        post = Post.objects.create(title="글", stage=Stage.REVIEW)
        self.client.post(reverse("writing:status", args=[post.pk]), {"field": "review_status", "value": "done"})
        self.client.post(reverse("writing:move"), {"pk": post.pk, "to": "post"})
        self.client.post(reverse("writing:move"), {"pk": post.pk, "to": "review"})
        post.refresh_from_db()
        self.assertEqual(post.review_status, Post.Review.DONE)

    def test_publish_done_sets_date(self):
        post = Post.objects.create(title="글", stage=Stage.POST)
        self.client.post(reverse("writing:status", args=[post.pk]), {"field": "publish_status", "value": "done"})
        post.refresh_from_db()
        self.assertTrue(post.is_published)
        self.assertIsNotNone(post.published_on)

    def test_invalid_status_rejected(self):
        post = Post.objects.create(title="글", stage=Stage.POST)
        self.client.post(reverse("writing:status", args=[post.pk]), {"field": "publish_status", "value": "doing"})
        self.client.post(reverse("writing:status", args=[post.pk]), {"field": "stage", "value": "temp"})
        post.refresh_from_db()
        self.assertEqual(post.publish_status, Post.Publish.TODO)
        self.assertEqual(post.stage, Stage.POST)

    def test_edit_and_delete(self):
        post = Post.objects.create(title="글", stage=Stage.REVIEW)
        res = self.client.post(reverse("writing:edit", args=[post.pk]),
                               {"title": "고친 글", "summary": "", "body": "본문", "review_status": "doing"})
        self.assertRedirects(res, reverse("writing:review"))
        post.refresh_from_db()
        self.assertEqual((post.title, post.review_status), ("고친 글", Post.Review.DOING))
        self.client.post(reverse("writing:delete", args=[post.pk]))
        self.assertFalse(Post.objects.exists())
