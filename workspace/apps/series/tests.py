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
        self.assertContains(res, f'href="{INDEX}"')  # 메뉴 (블로그·카페 › memorily 티스토리 › 블로그 자동화)
        from apps.core.menus import MENUS
        blog = next(m for m in MENUS if m.key == "blog")
        tistory = next(c for c in blog.children if c.key == "memorily_tistory")
        self.assertIn("series", [g.key for g in tistory.children])
        self.assertNotIn("series", [m.key for m in MENUS])
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
        # 가운데 요약의 '내 추가 설명' → 글쓰기 때 '필요했던 것' 아래 내 말 그대로
        self.client.post(reverse("series:note", args=[ep.pk]), {"note": "폰에서 열어 보려다\r\n막혔다."})
        ep.refresh_from_db()
        self.assertEqual(ep.note, "폰에서 열어 보려다\n막혔다.")
        res = self.client.post(reverse("series:make_post", args=[ep.pk]))
        ep.refresh_from_db()
        post = ep.post
        self.assertEqual((post.target, post.stage, ep.status), ("memorily", "temp", "doing"))
        self.assertTrue(post.title.startswith("[AI 와 블로그 자동화 만들기 EP.2]"))
        # 연재 구성대로, 흐름 줄은 말머리(처음 · 부족 · 바꿈 …)에 따라 나뉘어 들어간다
        for head in ("## 필요했던 것\nPC 에서만", "싶었다.\n\n폰에서 열어 보려다\n막혔다.\n\n## 처음 만든 것",
                     "## 처음 만든 것\n\n- (10-13) PythonAnywhere",
                     "## 써 보니 부족했던 점\n\n- 바꿀 때마다", "## 이렇게 바꿨다\n\n- (10-13) '서버 코드 갱신'",
                     "\n[사진] ", "## 지금 모습"):
            self.assertIn(head, post.body)
        self.assertRedirects(res, f"{INDEX}?ep={ep.pk}", fetch_redirect_response=False)  # 이 화면 오른쪽에 그 글
        res = self.client.get(INDEX, {"ep": ep.pk})
        self.assertContains(res, f'href="{reverse("writing:edit", args=[post.pk])}"')
        self.assertContains(res, "<h2>필요했던 것</h2>", html=False)
        self.client.post(reverse("series:make_post", args=[ep.pk]))  # 두 번 눌러도 글은 하나
        self.assertEqual(Post.objects.filter(target="memorily").count(), 1)

        res = self.client.post(f"{INDEX}?ep={ep.pk}&edit=1", {"number": 2, "title": "바꾼 제목", "hook": "",
                                                              "period": "10-13", "points": "가\n나", "sources": ""})
        ep.refresh_from_db()
        self.assertEqual((ep.title, ep.point_list), ("바꾼 제목", ["가", "나"]))
        res = self.client.post(f"{INDEX}?new=1", {"number": 16, "title": "새 회차", "hook": "", "period": "",
                                                  "points": "", "sources": ""})
        self.assertTrue(Episode.objects.filter(number=16, title="새 회차").exists())


class ShotTests(TestCase):
    """회차 사진: SERIES_SHOTS_DIR/EP01/<순서>_<말머리>_<설명>.jpg"""

    def setUp(self):
        import tempfile
        from pathlib import Path
        self.client.force_login(get_user_model().objects.create_user("tester", password="pw-test-1234"))
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        folder = Path(self.tmp.name) / "EP02"
        folder.mkdir()
        (folder / "1_처음_서버 첫 화면.jpg").write_bytes(b"jpg-1")
        (folder / "2_그때_설정 (10-14).jpg").write_bytes(b"jpg-2")
        (folder / "메모.txt").write_text("사진 아님", encoding="utf-8")

    def test_list_serve_and_skeleton(self):
        from django.test import override_settings
        with override_settings(SERIES_SHOTS_DIR=self.tmp.name):
            ep = Episode.objects.get(number=2)
            res = self.client.get(INDEX, {"ep": ep.pk})
            self.assertEqual([(s["word"], s["label"], s["original"]) for s in res.context["shots"]],
                             [("처음", "서버 첫 화면", False), ("그때", "설정 (10-14)", True)])
            url = reverse("series:shot", args=[2, "1_처음_서버 첫 화면.jpg"])
            self.assertContains(res, f'src="{url}"')
            res = self.client.get(url)
            self.assertEqual(b"".join(res.streaming_content), b"jpg-1")
            res.close()
            self.assertEqual(self.client.get(reverse("series:shot", args=[2, "메모.txt"])).status_code, 404)
            self.assertEqual(self.client.get(reverse("series:shot", args=[2, "..%2F..%2Fsettings.py"])).status_code, 404)
            self.client.post(reverse("series:make_post", args=[ep.pk]))
            ep.refresh_from_db()
            body = ep.post.body
            self.assertIn("[사진] 서버 첫 화면 — EP02/1_처음_서버 첫 화면.jpg", body)  # 처음 만든 것 아래
            self.assertIn("[사진] 설정 (10-14) — EP02/2_그때_설정 (10-14).jpg", body)  # 그때 사진은 '이렇게 바꿨다' 아래
            self.assertLess(body.index("## 처음 만든 것"), body.index("서버 첫 화면"))
            self.assertLess(body.index("## 이렇게 바꿨다"), body.index("설정 (10-14)"))
