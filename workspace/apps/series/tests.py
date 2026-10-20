from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.writing.models import Post

from .models import Episode

INDEX = reverse("series:index")


class SeriesTests(TestCase):
    def setUp(self):
        self.client.force_login(get_user_model().objects.create_user("tester", password="pw-test-1234"))

    def test_menu_and_seeded_episodes(self):
        res = self.client.get(INDEX)
        self.assertEqual(res.context["ACTIVE_MENU"], "series")
        self.assertContains(res, f'href="{INDEX}"')  # 메뉴
        self.assertEqual(Episode.objects.count(), 15)
        self.assertEqual(res.context["current"].number, 1)  # 고른 게 없으면 1회
        self.assertContains(res, "빈 서버에 화면 세 개")
        self.assertContains(res, "글 관리 · 글 보기 · 글 매핑 관리")  # 화면 칸
        ep = Episode.objects.get(number=11)  # 사이트별 템플릿 · 변환
        res = self.client.get(INDEX, {"ep": ep.pk})
        self.assertContains(res, "cp949")

    def test_status_make_post_and_edit(self):
        ep = Episode.objects.get(number=4)
        self.client.post(reverse("series:status", args=[ep.pk]), {"value": "done"})
        ep.refresh_from_db()
        self.assertEqual(ep.status, "done")

        ep = Episode.objects.get(number=2)
        res = self.client.post(reverse("series:make_post", args=[ep.pk]))
        ep.refresh_from_db()
        post = ep.post
        self.assertEqual((post.target, post.stage, ep.status), ("memorily", "temp", "doing"))
        self.assertTrue(post.title.startswith("[AI 와 블로그 자동화 만들기 EP.2]"))
        # 연재 구성대로, 흐름 줄은 말머리(처음 · 부족 · 바꿈 …)에 따라 나뉘어 들어간다
        for head in ("## 필요했던 것\nPC 에서만", "## 처음 만든 것\n\n- (10-13) PythonAnywhere",
                     "## 써 보니 부족했던 점\n\n- 바꿀 때마다", "## 이렇게 바꿨다\n\n- (10-13) '서버 코드 갱신'",
                     "[사진] 바꾼 뒤 화면", "## 지금 모습"):
            self.assertIn(head, post.body)
        self.assertRedirects(res, f"{reverse('posts:view')}?stage=temp&p=tistory:{post.pk}", fetch_redirect_response=False)
        self.client.post(reverse("series:make_post", args=[ep.pk]))  # 두 번 눌러도 글은 하나
        self.assertEqual(Post.objects.filter(target="memorily").count(), 1)

        res = self.client.post(f"{INDEX}?ep={ep.pk}&edit=1", {"number": 2, "title": "바꾼 제목", "hook": "",
                                                              "period": "10-13", "points": "가\n나", "sources": ""})
        ep.refresh_from_db()
        self.assertEqual((ep.title, ep.point_list), ("바꾼 제목", ["가", "나"]))
        res = self.client.post(f"{INDEX}?new=1", {"number": 16, "title": "새 회차", "hook": "", "period": "",
                                                  "points": "", "sources": ""})
        self.assertTrue(Episode.objects.filter(number=16, title="새 회차").exists())
