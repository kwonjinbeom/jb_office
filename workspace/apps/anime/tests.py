import tempfile
from pathlib import Path
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.core.menus import build_nav, find_menu, menu_keys_for

from .models import AnimeTitle


class AnimeTests(TestCase):
    def setUp(self):
        self.client.force_login(get_user_model().objects.create_user("tester", password="pw-test-1234"))
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        (root / "00_작업순서.md").write_text("# 글 쓰는 순서\n\n공통", encoding="utf-8")
        (root / "02_블리치.md").write_text("# 블리치\n\n상태: 준비\n\n| a | b |\n|---|---|\n| 1 | 2 |", encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def test_lists_guide_and_works(self):
        with override_settings(ANIME_DIR=self.tmp.name):
            res = self.client.get(reverse("anime:index"))
            self.assertContains(res, "글 쓰는 순서")
            self.assertContains(res, "준비")
            self.assertEqual(res.context["work_count"], 6)  # 이미 쓴 6작품이 담겨 있다 (migration 0002)
            res = self.client.get(reverse("anime:index"), {"d": "02_블리치"})
            self.assertContains(res, "<table>")  # md 표가 그려진다
            self.assertEqual(res.context["current"]["anime"].title, "블리치")  # md 와 애니가 이어진다

    def test_catalog_seeded_with_status(self):
        self.assertGreaterEqual(AnimeTitle.objects.count(), 30)
        self.assertEqual(AnimeTitle.objects.get(title="나루토").status, "published")
        self.assertEqual(set(AnimeTitle.objects.filter(picked=True).values_list("status", flat=True)), {"published", "written"})
        self.assertEqual(AnimeTitle.objects.get(title="진격의 거인").status, "todo")

    def test_pick_unpick_status_add_delete(self):
        with override_settings(ANIME_DIR=self.tmp.name):
            aot = AnimeTitle.objects.get(title="진격의 거인")
            self.client.post(reverse("anime:pick", args=[aot.pk]), {"picked": "1", "next": "https://evil.example/"})
            aot.refresh_from_db()
            self.assertTrue(aot.picked)
            res = self.client.get(reverse("anime:index"), {"a": aot.pk})
            self.assertEqual(res.context["current"]["anime"], aot)
            self.assertContains(res, "아직 작품 md 가 없습니다")
            self.client.post(reverse("anime:status", args=[aot.pk]), {"status": "doing"})
            self.client.post(reverse("anime:status", args=[aot.pk]), {"status": "nope"})  # 없는 상태는 무시
            aot.refresh_from_db()
            self.assertEqual(aot.status, "doing")
            res = self.client.post(reverse("anime:pick", args=[aot.pk]), {"picked": "0", "next": "https://evil.example/"})
            self.assertRedirects(res, reverse("anime:index"), fetch_redirect_response=False)  # 바깥 주소로는 안 간다
            aot.refresh_from_db()
            self.assertFalse(aot.picked)
            self.client.post(reverse("anime:add"), {"title": "  새 장편  "})
            self.client.post(reverse("anime:add"), {"title": "새 장편"})  # 같은 제목은 하나만
            self.assertEqual(AnimeTitle.objects.filter(title="새 장편").count(), 1)
            new = AnimeTitle.objects.get(title="새 장편")
            self.assertEqual(new.order, AnimeTitle.objects.exclude(pk=new.pk).order_by("-order")[0].order + 10)
            self.client.post(reverse("anime:delete", args=[new.pk]))
            self.assertFalse(AnimeTitle.objects.filter(pk=new.pk).exists())
            self.assertTrue(AnimeTitle.all_objects.filter(pk=new.pk).exists())  # 휴지통

    def test_menu_has_memorily_tistory_level(self):
        """블로그·카페 › memorily 티스토리 › 블로그 자동화 · 애니 총정리 (2026-10-21 사용자)"""
        self.assertEqual(find_menu("anime").title, "애니 총정리")
        self.assertEqual(find_menu("series").title, "블로그 자동화")
        self.assertEqual(menu_keys_for("anime", "index"), ["anime"])
        blog = next(n for n in build_nav("anime") if n["menu"].key == "blog")
        group = next(c for c in blog["children"] if c["menu"].key == "memorily_tistory")
        self.assertTrue(blog["open"] and group["active"])
        self.assertEqual([g["menu"].key for g in group["children"]], ["series", "anime", "anime_seasons"])
        res = self.client.get(reverse("series:index"))
        self.assertContains(res, 'class="nav-sub-label active"')


class AnimeWriteRunTests(TestCase):
    """'글쓰기·변환' (2026-10-23 사용자): 원고 없는 담은 작품 → PC 터미널 claude 가 글쓰기부터 변환까지, 서버 넣기는 api_place."""

    def setUp(self):
        from apps.blog_rules.models import Blog
        from apps.blog_types.models import SiteCategory
        from apps.core.models import ROUTINE_BRIEF_TOKEN_KEY, AppSetting

        self.client.force_login(get_user_model().objects.create_user("tester", password="pw-test-1234"))
        AppSetting.set(ROUTINE_BRIEF_TOKEN_KEY, "tok")
        blog = Blog.objects.get(name="memorily")
        self.cat = (SiteCategory.objects.filter(blog=blog, name__startswith="애니").first()
                    or SiteCategory.objects.create(blog=blog, name="애니"))
        self.cat.concept = "애니 회차정리 글 — 작품 하나에 글 하나 (시험)"
        self.cat.save()
        self.aot = AnimeTitle.objects.get(title="진격의 거인")
        self.aot.picked = True
        self.aot.save()

    def test_write_run_prompt_for_titles_without_draft(self):
        res = self.client.get(reverse("anime:index"))
        self.assertEqual(res.context["to_write"], [self.aot])  # 원고 완료 작품은 빠진다
        self.assertContains(res, "글쓰기·변환 1")
        j = self.client.post(reverse("anime:write_run")).json()
        self.assertTrue(j["prompt"].startswith("# 애니 총정리"))
        self.assertIn(f"<!-- 애니 총정리 작품: a{self.aot.pk} -->", j["prompt"])
        self.assertIn("진격의 거인 회차정리 애니만화 환산기 명장면 등 모음", j["prompt"])
        self.assertIn("(시험)", j["prompt"])  # 카테고리 컨셉이 들어간다
        self.assertIn(reverse("anime:api_place", args=[self.aot.pk]) + "?token=tok", j["prompt"])
        self.assertEqual(j["count"], 1)
        self.aot.refresh_from_db()
        self.assertEqual(self.aot.status, "doing")

    def test_api_place_puts_draft_and_marks_written(self):
        from apps.blog_types.models import Placement

        url = reverse("anime:api_place", args=[self.aot.pk])
        self.assertEqual(self.client.post(url + "?token=x", {"folder": "T1_a"}).status_code, 403)
        self.assertEqual(self.client.post(url + "?token=tok", {"folder": "../x"}).status_code, 400)
        draft = (Path(settings.REPO_ROOT) / "콘텐츠/블로그_카페/포스팅자동화/원고/T111_히로아카환산기/원고.md").read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as tmp, override_settings(REPO_ROOT=Path(tmp)):
            self.assertEqual(self.client.post(url + "?token=tok", {"folder": "T999_진격환산기"}).status_code, 404)
            folder = Path(tmp, "콘텐츠", "블로그_카페", "포스팅자동화", "원고", "T999_진격환산기")
            folder.mkdir(parents=True)
            (folder / "원고.md").write_text(draft.replace("나의 히어로 아카데미아 회차정리", "진격의 거인 회차정리"), encoding="utf-8")
            res = self.client.post(url + "?token=tok", {"folder": "T999_진격환산기", "doc": "07_진격의거인.md"})
        self.assertContains(res, "ok 진격의 거인")
        pl = Placement.objects.get(site_category=self.cat, tistory_post__title="진격의 거인 회차정리 애니만화 환산기 명장면 등 모음")
        self.assertEqual(pl.convert_status, "done")
        self.aot.refresh_from_db()
        self.assertEqual((self.aot.status, self.aot.doc_key), ("written", "07_진격의거인"))

    def test_local_run_opens_one_terminal_per_title(self):
        from apps.routines.local_run import start

        text = self.client.post(reverse("anime:write_run")).json()["prompt"]
        link = "jbroutine:anime?key=an-1&day=2026-10-23"
        with tempfile.TemporaryDirectory() as tmp, override_settings(BASE_DIR=Path(tmp)), \
                patch("apps.routines.local_run.WINDOWS", True), patch("apps.routines.local_run.find_claude", return_value="claude"), \
                patch("apps.routines.local_run.subprocess.Popen") as popen:
            with self.assertRaises(ValueError):
                start(link, "# 사이트 변환 · x")
            self.assertIn("1작품", start(link, text.replace("\n", "\r\n")))
            folder = Path(tmp) / ".routine"
            body = (folder / f"anime-2026-10-23-1-a{self.aot.pk}.md").read_text(encoding="utf-8")
            self.assertTrue(body.startswith("## 진격의 거인 — 회차정리 글쓰기·변환"))
            self.assertIn("workspace/.routine/done/", body)
            chain = (folder / "all-chain.ps1").read_text(encoding="utf-8-sig")
            self.assertEqual(chain.count("Start-Process"), 1)
            self.assertIn("애니 글쓰기·변환 1/1 진격의 거인", chain)
            self.assertIn("Bash(python *)", (folder / "settings-extra.json").read_text(encoding="utf-8"))
            popen.assert_called_once()
