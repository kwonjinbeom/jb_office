from django.contrib.auth import get_user_model
from django.conf import settings
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.blog_rules.models import Blog

from .models import Category, Placement, PostType, Section, SiteCategory, SubType

INDEX = reverse("blog_types:index")


def legacy_tree():
    """0017 이전 글 분류(판매 수익·광고 수익·IT/AI 와 그 아래)를 되살린다.
    아래 테스트들은 분류 화면·글 넣기 같은 동작을 옛 시드 이름으로 확인한다 (2026-10-22 새 분류는 SimpleClassesTests)."""
    from apps.core.models import TrashEntry
    Section.all_objects.filter(name__in=["눈잎", "black_lukey", "밤밤", "memorily", "워드프레스"]).delete()
    for model in (Section, Category, PostType, SubType):
        model.all_objects.update(deleted_at=None)
    TrashEntry.objects.filter(model_label="blog_types.section").delete()


class BlogTypesTests(TestCase):
    def setUp(self):
        legacy_tree()
        user = get_user_model().objects.create_user("tester", password="pw-test-1234")
        self.client.force_login(user)

    @staticmethod
    def cat(code):
        """판매 수익 (커넥트)의 카테고리. 기호는 대분류마다 A 부터라 대분류를 함께 지정한다."""
        return Category.objects.get(section__name="판매 수익 (커넥트)", code=code)

    def test_seed_from_08(self):
        # 0002 migration 이 08 문서 표를 넣는다 (테스트 DB 도 migrate 로 만든다)
        # 0004: A~G 는 첫 대분류 '판매 수익 (커넥트)' 아래로 간다
        connect = Section.objects.get(name="판매 수익 (커넥트)")
        self.assertEqual(list(connect.categories.values_list("code", flat=True)), list("ABCDEFG"))
        self.assertEqual(connect.name, "판매 수익 (커넥트)")
        self.assertEqual(connect.categories.count(), 7)
        self.assertEqual(PostType.objects.filter(category__section=connect).count(), 14)
        self.assertEqual(self.cat("G").platform, Category.Platform.NAVER)
        season = PostType.objects.get(name="시즌 달력")
        self.assertEqual([s.name for s in season.subs.all()], ["세일 행사", "계절 품목", "기념일·시험"])

    def test_tree_shows_names_only_and_menu(self):
        res = self.client.get(INDEX)
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "판매 수익 (커넥트)")
        self.assertContains(res, "문제 해결")
        self.assertContains(res, "시즌 달력")
        self.assertContains(res, "세일 행사")  # 3단계까지 트리에 보인다
        self.assertNotContains(res, "K-세일페스타")  # 하위 설명은 트리에 없다
        self.assertContains(res, "모든 사이트")  # 위 칸: 아무것도 안 고르면 모든 매핑
        self.assertContains(res, "글 관리")  # 블로그·카페 아래 중메뉴
        self.assertContains(res, "모든 글")  # 글 분류는 하나 (티스토리·네이버 나눔 없음)
        self.assertNotContains(res, 'href="?w=naver"')

    def test_select_shows_path_children_and_detail(self):
        season = PostType.objects.get(name="시즌 달력")
        res = self.client.get(INDEX, {"sel": season.sel})
        self.assertEqual([label for label, _ in res.context["cpath"]], ["모든 글", "판매 수익 (커넥트)", "C. 타이밍", "시즌 달력"])
        self.assertEqual(res.context["open"], {season.category.section.sel, season.category.sel, season.sel})
        self.assertIsNone(res.context["bottom_form"])  # 고치는 칸은 연필(edit)로만 연다
        sub = season.subs.first()
        res = self.client.get(INDEX, {"sel": sub.sel, "edit": "1"})
        self.assertContains(res, "K-세일페스타")  # 고치기를 열면 설명이 보인다

    def test_quick_add_each_level(self):
        res = self.client.post(reverse("blog_types:add", args=["section"]), {"name": "일상·브이로그"})
        daily = Section.objects.get(name="일상·브이로그")
        self.assertRedirects(res, f"{INDEX}?sel={daily.sel}", fetch_redirect_response=False)
        self.client.post(reverse("blog_types:add", args=["category"]), {"name": "카페", "parent": daily.sel})
        self.assertEqual(daily.categories.get().code, "A")  # 기호는 대분류마다 A 부터
        connect = Section.objects.get(name="판매 수익 (커넥트)")
        res = self.client.post(reverse("blog_types:add", args=["category"]), {"name": "구독", "parent": connect.sel})
        h = Category.objects.get(name="구독")
        self.assertEqual(h.code, "H")
        self.assertRedirects(res, f"{INDEX}?sel={h.sel}", fetch_redirect_response=False)
        self.client.post(reverse("blog_types:add", args=["type"]), {"name": "해지 비교", "parent": h.sel})
        t = h.types.get()
        self.client.post(reverse("blog_types:add", args=["sub"]), {"name": "OTT", "parent": t.sel})
        self.client.post(reverse("blog_types:add", args=["sub"]), {"name": "멤버십", "parent": t.sel})
        self.assertEqual([s.name for s in t.subs.all()], ["OTT", "멤버십"])
        # 단계가 안 맞으면(카테고리 밑에 하위, 부모 없는 카테고리) 넣지 않는다
        self.client.post(reverse("blog_types:add", args=["sub"]), {"name": "잘못", "parent": h.sel})
        self.client.post(reverse("blog_types:add", args=["category"]), {"name": "고아"})
        self.assertFalse(SubType.objects.filter(name="잘못").exists())
        self.assertFalse(Category.objects.filter(name="고아").exists())

    def test_move_reorders_siblings(self):
        season = PostType.objects.get(name="시즌 달력")
        last = season.subs.last()
        self.client.post(reverse("blog_types:move", args=["sub", last.pk]), {"dir": "up", "back": season.sel})
        self.assertEqual([s.name for s in season.subs.all()], ["세일 행사", "기념일·시험", "계절 품목"])
        first_cat = self.cat("A")
        self.client.post(reverse("blog_types:move", args=["category", first_cat.pk]), {"dir": "up"})
        self.assertEqual(first_cat.section.categories.first().code, "A")  # 맨 위는 더 못 올라간다
        daily = Section.objects.create(name="일상·브이로그", order=9)
        for _ in range(2):  # IT/AI 위로, 광고 수익 위로
            self.client.post(reverse("blog_types:move", args=["section", daily.pk]), {"dir": "up"})
        self.assertEqual([g.name for g in Section.objects.all()], ["판매 수익 (커넥트)", "일상·브이로그", "광고 수익 (조회수)", "IT/AI"])

    def test_save_detail(self):
        sub = SubType.objects.get(name="세일 행사")
        res = self.client.post(reverse("blog_types:save", args=["sub", sub.pk]), {"name": "큰 세일", "note": "블프 위주"})
        self.assertRedirects(res, f"{INDEX}?sel={sub.sel}", fetch_redirect_response=False)
        sub.refresh_from_db()
        self.assertEqual((sub.name, sub.note), ("큰 세일", "블프 위주"))
        res = self.client.post(reverse("blog_types:save", args=["sub", sub.pk]), {"name": "", "note": ""})
        self.assertEqual(res.status_code, 200)  # 이름이 비면 저장하지 않고 오류를 보여 준다
        self.assertTrue(res.context["bottom_form"].errors)

    def test_delete_category_removes_children(self):
        c = self.cat("C")
        res = self.client.get(reverse("blog_types:delete", args=["category", c.pk]))
        self.assertContains(res, "타입 2개, 하위 3개")
        self.client.post(reverse("blog_types:delete", args=["category", c.pk]))
        self.assertFalse(SubType.objects.filter(name="세일 행사").exists())

    def test_delete_section_removes_everything_inside(self):
        connect = Section.objects.get(name="판매 수익 (커넥트)")
        res = self.client.get(reverse("blog_types:delete", args=["section", connect.pk]))
        self.assertContains(res, "카테고리 7개, 타입 14개, 하위 6개")
        self.client.post(reverse("blog_types:delete", args=["section", connect.pk]))
        self.assertFalse(Category.objects.filter(name="문제 해결").exists())
        self.assertEqual(Category.objects.count(), 11)  # 다른 대분류(광고 수익 8 · IT/AI 3)는 그대로

    def test_views_section_from_09(self):
        views = Section.objects.get(name="광고 수익 (조회수)")
        self.assertEqual(list(views.categories.values_list("code", flat=True)), list("ABCDEFGH"))
        finance = views.categories.get(name="금융·시장")
        daily = finance.types.get(name="일일 시황 · 오늘 ○○ 왜")
        self.assertEqual(daily.example_list, ["오늘 코스피 하락 이유", "나스닥 상승 이유"])
        self.assertIn("투자 권유 금지", finance.note)
        from importlib import import_module

        from django.apps import apps as django_apps

        import_module("apps.blog_types.migrations.0006_views_section").forward(django_apps, None)
        self.assertEqual(Section.objects.filter(name="광고 수익 (조회수)").count(), 1)  # 두 번 넣지 않는다

    def test_seed_does_not_overwrite(self):
        from importlib import import_module

        from django.apps import apps as django_apps

        seed = import_module("apps.blog_types.migrations.0002_seed_08").seed
        before = Category.objects.count()
        Category.objects.filter(section__name="판매 수익 (커넥트)", code="A").update(name="내가 바꾼 이름")
        seed(django_apps, None)
        self.assertEqual(Category.objects.count(), before)
        self.assertEqual(self.cat("A").name, "내가 바꾼 이름")


class SiteCategoryTests(TestCase):
    """사이트 카테고리: 사이트(규칙 화면의 블로그) › 카테고리 › 하위 카테고리"""

    def setUp(self):
        legacy_tree()
        user = get_user_model().objects.create_user("tester", password="pw-test-1234")
        self.client.force_login(user)
        self.memorily = Blog.objects.get(name="memorily")

    def add(self, parent_sel, name):
        return self.client.post(reverse("blog_types:add", args=["sitecat"]), {"parent": parent_sel, "name": name})

    def test_seed_real_categories(self):
        names = list(SiteCategory.objects.filter(blog=self.memorily, parent=None).values_list("name", flat=True))
        # AI 는 0021 (2026-10-23) → IT·AI (0054, 2026-10-31 사용자). 옛 개발 카테고리 9개는 0042 에서 휴지통 (2026-10-27 사용자)
        self.assertEqual(names, ["IT·AI"])
        top = SiteCategory.objects.get(blog=self.memorily, name="IT·AI")
        self.assertFalse(top.heading_bar)
        # 블로그에는 없는 컨셉 갈래 넷 (0052 의 총정리 셋을 옮기고 AI 소식에 옛 AI 컨셉)
        kids = list(top.children.values_list("name", "branch"))
        self.assertEqual(kids, [("AI 소식", True), ("무료 AI 툴", True), ("이달의 AI", True), ("IT 할인", True)])
        roundup = SiteCategory.objects.get(blog=self.memorily, name="IT 할인")
        self.assertEqual((str(roundup), roundup.short), ("IT·AI (컨셉: IT 할인)", "IT·AI (컨셉: IT 할인)"))
        self.assertIn("주제그림.py", roundup.concept)
        self.assertIn("IT할인_*.json", roundup.concept)
        self.assertNotIn("정리카드", roundup.concept)
        self.assertIn("AI 소식:", SiteCategory.objects.get(blog=self.memorily, name="AI 소식").concept)
        self.assertTrue(SiteCategory.objects.get(blog=self.memorily, name="AI 소식").heading_bar)
        self.assertTrue(SiteCategory.objects.get(blog=self.memorily, name="이달의 AI").heading_bar)
        self.assertFalse(SiteCategory.objects.get(blog=self.memorily, name="무료 AI 툴").heading_bar)
        self.assertTrue(SiteCategory.all_objects.filter(blog=self.memorily, name="Java", deleted_at__isnull=False).exists())
        self.assertEqual(SiteCategory.objects.filter(blog__name="black_lukey").count(), 3)  # 낙서장 · videolog (시험 DB 의 옛 값) + 세일 이벤트 (0053)
        self.assertEqual(SiteCategory.objects.filter(blog__name="눈잎").count(), 7)  # 0019 티스토리 화면 그대로 + 생활 (0040)

    def test_anime_branches(self):
        """애니 아래 컨셉 갈래 둘 (0054, 2026-10-31 사용자): 옛 애니 컨셉은 회차정리로, 애니 글의 넣은 곳도 회차정리로. 트리에 '컨셉' 표시"""
        from importlib import import_module
        from django.apps import apps as django_apps
        from apps.writing.models import Post
        mig = import_module("apps.blog_types.migrations.0054_memorily_branches")
        anime = SiteCategory.objects.create(blog=self.memorily, name="애니", concept="애니 회차정리 글 — 작품 하나에 글 하나")
        post = Post.objects.create(title="블리치 환산기", stage="post")
        pl = Placement.objects.create(site_category=anime, tistory_post=post)
        mig.forward(django_apps, None)
        kids = {c.name: c for c in anime.children.all()}
        self.assertEqual(list(kids), ["회차정리", "분기 신작"])
        self.assertIn("작품 하나에 글 하나", kids["회차정리"].concept)
        self.assertIn("'분기'", kids["분기 신작"].concept)
        pl.refresh_from_db()
        self.assertEqual(str(pl.site_category), "애니 (컨셉: 회차정리)")
        res = self.client.get(INDEX)
        self.assertContains(res, '<span class="cat-branch">컨셉</span>')
        mig.forward(django_apps, None)  # 두 번 돌려도 그대로
        self.assertEqual(anime.children.count(), 2)

    def test_tree_shows_both_grids(self):
        res = self.client.get(INDEX)
        self.assertContains(res, "글 분류")
        self.assertContains(res, "사이트 카테고리")
        self.assertContains(res, "Korea Travel")
        self.assertContains(res, "카테고리 없음")  # 눈잎·밤밤
        res = self.client.get(INDEX, {"sel": self.memorily.sel})
        self.assertContains(res, "https://jinbaam.tistory.com/")
        self.assertNotContains(res, "자세한 내용 · 고치기")  # 사이트 자체는 규칙 화면에서 고친다

    def test_add_edit_move_delete(self):
        self.add(self.memorily.sel, "AI 이야기")
        top = SiteCategory.objects.get(name="AI 이야기")
        self.assertEqual((top.blog, top.parent, top.order), (self.memorily, None, 11))
        self.add(top.sel, "Claude Code")
        sub = SiteCategory.objects.get(name="Claude Code")
        self.assertEqual(sub.parent, top)
        res = self.add(sub.sel, "3단")  # 하위 카테고리 아래로는 못 만든다
        self.assertFalse(SiteCategory.objects.filter(name="3단").exists())
        self.client.post(reverse("blog_types:save", args=["sitecat", top.pk]), {"name": "AI 개발기", "note": "새 축"})
        top.refresh_from_db()
        self.assertEqual((top.name, top.note), ("AI 개발기", "새 축"))
        self.client.post(reverse("blog_types:move", args=["sitecat", top.pk]), {"dir": "up"})
        self.assertEqual(SiteCategory.objects.filter(blog=self.memorily, parent=None)[0].name, "AI 개발기")
        res = self.client.get(reverse("blog_types:delete", args=["sitecat", top.pk]))
        self.assertContains(res, "하위 카테고리 1개")
        self.client.post(reverse("blog_types:delete", args=["sitecat", top.pk]))
        self.assertFalse(SiteCategory.objects.filter(name__in=["AI 개발기", "Claude Code"]).exists())
        self.assertEqual(SiteCategory.all_objects.filter(name="Claude Code").count(), 1)  # 휴지통에서 복원할 수 있다

    def test_site_is_not_editable_here(self):
        self.assertEqual(self.client.post(reverse("blog_types:save", args=["site", self.memorily.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse("blog_types:delete", args=["site", self.memorily.pk])).status_code, 404)


class PostManageTests(TestCase):
    """글 관리: 글에 붙는 분류, 글쓰기 목록의 분류별 묶음, 사이트 카테고리에 글 넣기(매핑)"""

    def setUp(self):
        legacy_tree()
        user = get_user_model().objects.create_user("tester", password="pw-test-1234")
        self.client.force_login(user)
        from apps.naver_writing.models import Post as NaverPost
        from apps.writing.models import Post as TistoryPost
        self.TistoryPost, self.NaverPost = TistoryPost, NaverPost
        self.season = PostType.objects.get(name="시즌 달력")
        self.sale = self.season.subs.get(name="세일 행사")

    def test_form_sets_classification_and_list_groups(self):
        from apps.writing.forms import PostForm
        post = self.TistoryPost.objects.create(title="블프 달력", stage="post")
        form = PostForm({"title": "블프 달력", "classification": self.sale.sel, "write_status": "todo",
                         "publish_status": "todo"}, instance=post, stage="post")
        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        post.refresh_from_db()
        self.assertEqual((post.bt_category, post.bt_type, post.bt_sub), (self.season.category, self.season, self.sale))
        self.assertEqual(PostForm(instance=post, stage="post").fields["classification"].initial, self.sale.sel)
        self.TistoryPost.objects.create(title="분류 없는 글", stage="post")
        res = self.client.get(reverse("writing:posts"))
        labels = [g["label"] for g in res.context["groups"]]
        self.assertEqual(labels, ["판매 수익 (커넥트) › C. 타이밍 › 시즌 달력 › 세일 행사", "미분류"])  # 미분류는 맨 아래

    def test_choices_are_the_same_for_both_editors(self):
        from apps.blog_types import classify
        g = Category.objects.get(section__name="판매 수익 (커넥트)", code="G")  # 예전엔 네이버 전용이던 G 도 모두에게
        self.assertEqual(classify.choices("tistory"), classify.choices("naver"))
        self.assertIn(g.sel, [v for _, rows in classify.choices()[1:] for v, _ in rows])

    def test_class_node_lists_posts_of_that_writer(self):
        from apps.blog_types import classify
        p = self.TistoryPost.objects.create(title="세일 정리", stage="post")
        classify.assign(p, self.sale.sel)
        p.save()
        self.TistoryPost.objects.create(title="아직 검토 중", stage="review", bt_category=self.season.category)
        self.TistoryPost.objects.create(title="발행한 글", stage="post", publish_status="done", bt_category=self.season.category)
        self.NaverPost.objects.create(title="네이버 편집기 글", stage="temp", bt_category=self.season.category)
        self.NaverPost.objects.create(title="네이버 발행예정", stage="post", bt_category=self.season.category)
        res = self.client.get(INDEX, {"sel": self.season.category.sel})
        self.assertEqual(sorted(x.title for x in res.context["posts"]),
                         ["네이버 발행예정", "세일 정리"])  # 아래 목록은 발행예정글만 (발행 완료는 뺀다), 두 편집기 함께

    def test_tree_counts_unpublished_posts(self):
        cat = self.season.category
        self.TistoryPost.objects.create(title="임시", stage="temp", bt_category=cat, bt_type=self.season, bt_sub=self.sale)
        self.TistoryPost.objects.create(title="검토", stage="review", bt_category=cat, bt_type=self.season)
        self.TistoryPost.objects.create(title="발행", stage="post", publish_status="done", bt_category=cat)
        self.NaverPost.objects.create(title="네이버", stage="temp", bt_category=cat)
        res = self.client.get(INDEX)
        tree = res.context["tree"]
        sec = next(g for g in tree["sections"] if g["obj"] == cat.section)
        c = next(x for x in sec["cats"] if x["obj"] == cat)
        t = next(x for x in c["types"] if x["obj"] == self.season)
        sub = next(x for x in t["subs"] if x["obj"] == self.sale)
        self.assertEqual((tree["count"], sec["count"], c["count"], t["count"], sub["count"]), (3, 3, 3, 2, 1))  # 네이버 편집기 글도 함께

    def test_send_between_writers(self):
        from apps.blog_types import classify
        post = self.TistoryPost.objects.create(title="블프 달력", stage="post", summary="요약", tags="블프",
                                               body="## 소제목\n본문")
        classify.assign(post, self.sale.sel)
        post.save()
        res = self.client.post(reverse("writing:send"), {"pk": post.pk, "next": "/blog/writing/posts/"})
        self.assertRedirects(res, "/blog/writing/posts/", fetch_redirect_response=False)
        copy = self.NaverPost.objects.get(title="블프 달력")
        self.assertEqual((copy.stage, copy.summary, copy.tags, copy.body), ("temp", "요약", "블프", "## 소제목\n본문"))
        self.assertEqual(copy.bt_sub, self.sale)
        self.assertTrue(self.TistoryPost.objects.filter(pk=post.pk).exists())  # 원래 글은 그대로
        # 분류는 편집기와 상관없이 그대로 따라간다 (예전 네이버 전용 G 도)
        g = Category.objects.get(section__name="판매 수익 (커넥트)", code="G")
        n = self.NaverPost.objects.create(title="단풍 패키지", stage="temp", bt_category=g)
        a = self.NaverPost.objects.create(title="두 번째", stage="temp")
        self.client.post(reverse("naver_writing:send"), {"ids": [n.pk, a.pk]})
        back = self.TistoryPost.objects.get(title="단풍 패키지")
        self.assertEqual(back.bt_category, g)
        self.assertTrue(self.TistoryPost.objects.filter(title="두 번째", stage="temp").exists())

    def test_place_post_in_site_category(self):
        memorily = Blog.objects.get(name="memorily")
        java = SiteCategory.objects.get_or_create(blog=memorily, name="Java")[0]
        post = self.TistoryPost.objects.create(title="자바 정리", stage="post")
        self.TistoryPost.objects.create(title="임시 글", stage="temp")
        res = self.client.get(INDEX, {"sel": java.sel})
        self.assertEqual([pk for pk, _ in res.context["candidates"]], [f"tistory:{post.pk}"])  # 발행예정글만 넣을 수 있다
        self.client.post(reverse("blog_types:place_add"), {"site_category": java.pk, "post": post.pk})
        placement = Placement.objects.get()
        self.assertEqual((placement.tistory_post, placement.status), (post, "unsaved"))  # 처음은 미발행
        self.client.post(reverse("blog_types:place_add"), {"site_category": java.pk, "post": post.pk})
        self.assertEqual(Placement.objects.count(), 1)  # 같은 곳에 두 번 넣지 않는다
        res = self.client.get(INDEX, {"sel": java.sel})
        self.assertEqual(res.context["candidates"], [])
        self.assertContains(res, "자바 정리")
        self.client.post(reverse("blog_types:place_status", args=[placement.pk]), {"value": "published"})
        placement.refresh_from_db()
        self.assertEqual(placement.status, "published")
        post.refresh_from_db()
        self.assertEqual(post.publish_status, "done")  # 넣은 곳을 발행 완료로 바꾸면 글도 발행 완료
        self.assertIsNotNone(post.published_on)
        self.client.post(reverse("blog_types:place_status", args=[placement.pk]), {"value": "unsaved"})
        post.refresh_from_db()
        self.assertEqual(post.publish_status, "todo")
        res = self.client.get(INDEX)
        self.assertContains(res, "memorily › Java")  # 글 분류 쪽에서도 넣은 곳이 보인다
        self.client.post(reverse("blog_types:place_remove", args=[placement.pk]))
        self.assertFalse(Placement.objects.exists())
        self.assertEqual(Placement.all_objects.count(), 1)  # 휴지통

    def test_any_post_goes_to_any_site(self):
        """플랫폼에 맞추는 건 사이트별 템플릿에서: 네이버 사이트에도 티스토리 편집기 글을 넣는다"""
        lukey = SiteCategory.objects.get(blog__name="black_lukey", name="낙서장")
        t = self.TistoryPost.objects.create(title="티스토리 글", stage="post")
        n = self.NaverPost.objects.create(title="네이버 글", stage="post")
        res = self.client.get(INDEX, {"sel": lukey.sel})
        self.assertEqual(sorted(pk for pk, _ in res.context["candidates"]), sorted([f"naver:{n.pk}", f"tistory:{t.pk}"]))
        draft = self.NaverPost.objects.create(title="네이버 임시", stage="temp")
        self.client.post(reverse("blog_types:place_add"), {"site_category": lukey.pk, "post": f"naver:{draft.pk}"})
        self.assertFalse(Placement.objects.exists())  # 발행예정글이 아니면 넣지 않는다
        self.client.post(reverse("blog_types:place_add"), {"site_category": lukey.pk, "post": f"tistory:{t.pk}"})
        self.client.post(reverse("blog_types:place_add"), {"site_category": lukey.pk, "post": f"naver:{n.pk}"})
        self.assertEqual({(p.tistory_post_id, p.naver_post_id) for p in Placement.objects.all()}, {(t.pk, None), (None, n.pk)})

    def test_trashing_post_takes_placement_along(self):
        java = SiteCategory.objects.get_or_create(blog=Blog.objects.get(name="memorily"), name="Java")[0]
        post = self.TistoryPost.objects.create(title="자바 정리", stage="post")
        Placement.objects.create(site_category=java, tistory_post=post)
        post.delete()
        self.assertFalse(Placement.objects.exists())


class SideNavTests(TestCase):
    def setUp(self):
        legacy_tree()
        user = get_user_model().objects.create_user("tester", password="pw-test-1234")
        self.client.force_login(user)

    def test_parent_menus_only_expand_and_list_child_keeps_old_page(self):
        res = self.client.get(reverse("studio:index"))
        self.assertContains(res, "창작콘텐츠 리스트")  # 블로그·카페 리스트는 뺐다 (listing=False)
        self.assertNotContains(res, "블로그·카페 리스트")
        self.assertContains(res, 'class="nav-item nav-toggle" data-nav-toggle')
        group = next(n for n in res.context["NAV"] if n["menu"].key == "studio")
        self.assertTrue(group["open"])
        self.assertTrue(group["children"][0]["active"])  # 리스트 중메뉴가 강조된다
        memos = next(n for n in res.context["NAV"] if n["menu"].key == "memos")
        self.assertEqual(memos["children"], [])  # 하위 없는 메뉴는 그대로
        video = next(n for n in res.context["NAV"] if n["menu"].key == "video")
        self.assertEqual(video["children"], [])  # 논의 현황을 빼서 (2026-10-23) 하위가 없다


class ClassifyExistingPostsTests(TestCase):
    def setUp(self):
        legacy_tree()

    def test_existing_titles_get_classified_once(self):
        from importlib import import_module

        from django.apps import apps as django_apps

        from apps.naver_writing.models import Post as NaverPost
        from apps.writing.models import Post as TistoryPost
        mig = import_module("apps.blog_types.migrations.0011_classify_existing_posts")
        flu = TistoryPost.objects.create(title=next(iter(mig.TISTORY)))
        kept = TistoryPost.objects.create(title=list(mig.TISTORY)[1], bt_category=Category.objects.get(
            section__name="판매 수익 (커넥트)", code="A"))
        ssd = NaverPost.objects.create(title=list(mig.NAVER)[1])
        mig.forward(django_apps, None)
        flu.refresh_from_db(), kept.refresh_from_db(), ssd.refresh_from_db()
        self.assertEqual((flu.bt_category.name, flu.bt_type.name), ("정책·내 돈", "대상·신청일 (내 줄 찾기)"))
        self.assertEqual(kept.bt_category.code, "A")  # 이미 정한 분류는 그대로
        self.assertEqual(ssd.bt_sub.name, "두 개만 비교")


@override_settings(WRITING_DRAFTS_DIR=settings.BASE_DIR / "없는-원고-폴더")  # 저장소 원고를 글 관리로 가져오지 않게
class PostHubTests(TestCase):
    """글 관리(티스토리·네이버 합친 화면)와 카테고리 관리의 미분류·글 쪽 넣기"""

    def setUp(self):
        legacy_tree()
        user = get_user_model().objects.create_user("tester", password="pw-test-1234")
        self.client.force_login(user)
        from apps.naver_writing.models import Post as NaverPost
        from apps.writing.models import Post as TistoryPost
        self.T, self.N = TistoryPost, NaverPost
        self.season = PostType.objects.get(name="시즌 달력")

    def test_view_screen_lists_stage_posts_with_category(self):
        """글 관리는 여러 건을 한 번에, 글 보기는 한 건씩. 글 관리 행을 누르면 글 보기(같은 조건)로 가고,
        글 보기 왼쪽에는 그 단계의 글 목록이 행마다 분류와 함께 나온다."""
        t1 = self.T.objects.create(title="티 글 하나", stage="temp", bt_category=self.season.category, bt_type=self.season)
        n1 = self.N.objects.create(title="네 글 둘", stage="temp", bt_category=self.season.category, bt_type=self.season)
        self.T.objects.create(title="다른 분류 글", stage="temp")
        self.T.objects.create(title="검토 중인 글", stage="review")
        view = reverse("posts:view")
        res = self.client.get(reverse("posts:index"), {"stage": "temp", "sel": self.season.sel})  # 예전 글 관리 주소 (2026-10-22)
        self.assertRedirects(res, f"{view}?stage=temp&sel={self.season.sel}", fetch_redirect_response=False)

        res = self.client.get(view, {"stage": "temp", "sel": self.season.sel, "p": f"tistory:{t1.pk}"})
        self.assertEqual(res.context["ACTIVE_MENU"], "posts_view")
        self.assertNotContains(res, 'data-bt-tree="class"')  # 글 보기에는 분류 트리가 없다
        self.assertEqual(sorted(p.title for p in res.context["pl_items"]), ["네 글 둘", "티 글 하나"])
        self.assertEqual(res.context["pl_current"].title, "티 글 하나")
        self.assertContains(res, f"{self.season.category.section.name} › {self.season.category.code}. {self.season.category.name} › {self.season.name}")
        self.assertContains(res, f"p=naver:{n1.pk}")  # 네이버 글도 같은 화면에서

        res = self.client.get(view, {"stage": "review", "view": "one"})  # 한 건씩: 고른 글이 없으면 그 단계의 첫 글
        self.assertEqual(res.context["post"].title, "검토 중인 글")
        self.assertEqual([p.title for p in res.context["pl_items"]], ["검토 중인 글"])
        self.T.objects.filter(stage="review").delete()
        res = self.client.get(view, {"stage": "review", "view": "one"})  # 글이 없는 단계
        self.assertContains(res, "검토글에 글이 없습니다")

        # 발행예정글은 한 건 대신 글 관리와 같은 전체 목록 (2026-10-20 사용자). 글을 누르면 그 글을 본다
        p1 = self.T.objects.create(title="발행할 글 하나", stage="post")
        self.N.objects.create(title="발행할 글 둘", stage="post")
        res = self.client.get(view, {"stage": "post"})
        self.assertEqual(res.context["ACTIVE_MENU"], "posts_view")
        self.assertEqual(sorted(p.title for p in res.context["posts"]), ["발행할 글 둘", "발행할 글 하나"])
        self.assertContains(res, f'href="{view}?stage=temp"')  # 단계 탭은 글 보기에 머문다
        self.assertContains(res, f'href="{reverse("site_templates:post")}?p=tistory:{p1.pk}&amp;back=')  # 제목은 변환 화면으로 (2026-10-22)
        self.assertContains(res, f'<a class="btn" href="{reverse("blog_types:index")}" title="사이트 카테고리에 넣기')  # 카테고리 관리로 가기
        res = self.client.get(view, {"stage": "post", "p": f"tistory:{p1.pk}"})
        self.assertEqual(res.context["post"].title, "발행할 글 하나")

    def test_temp_review_list_mode_bulk(self):
        """임시글·검토글 (2026-10-22 사용자): 한 건씩 · 목록(체크해서 한꺼번에 옮기기·삭제). 2026-10-31 사용자: 기본은 목록"""
        a = self.T.objects.create(title="임시 하나", stage="temp")
        b = self.N.objects.create(title="임시 둘", stage="temp")
        view = reverse("posts:view")
        res = self.client.get(view, {"stage": "temp", "view": "one"})  # 한 건씩 (글 화면) + 보기 바꾸기
        self.assertIn("post", res.context)
        self.assertContains(res, f'href="{view}?stage=temp"')
        res = self.client.get(view, {"stage": "temp"})  # 기본: 목록
        self.assertEqual(res.context["mode_urls"]["on"], "list")
        self.assertContains(res, f'href="{view}?stage=temp&amp;view=one"')
        self.assertEqual(sorted(p.title for p in res.context["posts"]), ["임시 둘", "임시 하나"])
        self.assertEqual(self.client.get(view, {"stage": "temp", "view": "list"}).context["mode_urls"]["on"], "list")  # 예전 주소도 목록
        self.assertContains(res, f'value="tistory:{a.pk}" form="ph-bulk"')
        self.assertContains(res, f'href="{view}?stage=temp&amp;view=one&amp;p=tistory:{a.pk}"')  # 제목은 한 건씩 보기로
        self.assertContains(res, f'href="{view}?stage=review"')  # 다른 단계 탭도 목록으로
        self.assertContains(res, 'name="to" value="review"')
        self.assertContains(res, 'data-trash-checked="ids"')
        self.assertNotContains(res, "변환 가능 글 전체 변환")  # 발행예정글 전용 칸은 없다
        back = f"{view}?stage=temp&view=list"
        res = self.client.post(reverse("posts:bulk"), {"ids": [f"tistory:{a.pk}", f"naver:{b.pk}"], "to": "review", "next": back})
        self.assertRedirects(res, back, fetch_redirect_response=False)
        a.refresh_from_db(); b.refresh_from_db()
        self.assertEqual((a.stage, b.stage), ("review", "review"))
        res = self.client.get(view, {"stage": "review", "view": "list"})
        self.assertContains(res, 'name="to" value="temp"')
        self.assertContains(res, 'name="to" value="post"')
        self.assertEqual(self.client.get(view, {"stage": "post", "view": "list"}).context["mode_urls"], None)  # 발행예정글은 늘 표

    def test_menu_has_view_screen(self):
        """블로그·카페 메뉴 (2026-10-22 사용자): 운영·예전 글 관리는 빼고, 글 보기 → 글 관리 · 글 매핑 관리 → 카테고리 관리.
        모니터링은 새로 (일자별 발행 수 · 발행 완료 자동 처리)"""
        res = self.client.get(reverse("posts:view"))
        self.assertContains(res, f'href="{reverse("posts:view")}"')
        blog = next(m for m in res.context["MENUS"] if m.key == "blog")
        # 2026-10-23 사용자: 모니터링이 맨 위, 글 관리는 접고 펴기만 하고 그 아래 임시·검토글 · 발행예정글 · 게시글 관리 · 카테고리 관리 · 사이트별 템플릿
        self.assertEqual([c.title for c in blog.children], ["통계현황", "모니터링", "글 관리", "memorily 티스토리"])  # 통계현황 (2026-10-23)
        self.assertEqual([c.title for c in blog.children[2].children],
                         ["임시·검토글", "발행예정글", "게시글 관리", "카테고리 관리", "사이트별 템플릿"])
        group = next(n for n in res.context["NAV"] if n["menu"].key == "blog")["children"][2]
        self.assertFalse(group["link"])  # 글 관리 이름 줄은 링크가 아니라 접기 (memorily 티스토리와 같다)
        self.assertEqual([s["active"] for s in group["children"]], [True, False, False, False, False])
        self.assertContains(res, '<button type="button" class="nav-sub-label active" data-nav-mid-toggle>글 관리</button>', html=False)
        self.assertContains(res, f'<a class="nav-item sub sub2 active" href="{reverse("posts:view")}"><span>임시·검토글</span></a>', html=False)
        self.assertContains(res, 'data-nav-mid="posts_hub"')  # 중메뉴 접기 버튼 (기본은 펼침)
        self.assertContains(res, 'data-nav-mid-toggle aria-expanded="true"')
        planned = self.client.get(reverse("posts:planned"))
        group = next(n for n in planned.context["NAV"] if n["menu"].key == "blog")["children"][2]
        self.assertEqual([s["active"] for s in group["children"]], [False, True, False, False, False])
        cats = self.client.get(reverse("blog_types:index"))
        group = next(n for n in cats.context["NAV"] if n["menu"].key == "blog")["children"][2]
        self.assertEqual([s["active"] for s in group["children"]], [False, False, False, True, False])

    def test_temp_review_has_no_planned_tab(self):
        """임시·검토글에서는 발행예정글 탭을 뺀다 (2026-10-23 사용자: 메뉴에 따로 있다). 발행예정글의 글을 볼 때만 그 탭이 남는다."""
        res = self.client.get(reverse("posts:view"), {"stage": "temp", "view": "list"})
        self.assertEqual([t["key"] for t in res.context["tabs"]], ["temp", "review"])
        self.assertNotContains(res, ">발행예정글<span")
        res = self.client.get(reverse("posts:view"), {"stage": "post"})
        self.assertEqual([t["key"] for t in res.context["tabs"]], ["temp", "review", "post"])

    def test_today_filter(self):
        from datetime import timedelta

        from django.utils import timezone

        self.T.objects.create(title="오늘 글", stage="temp")
        old = self.N.objects.create(title="어제 글", stage="temp")
        self.N.objects.filter(pk=old.pk).update(created_at=timezone.now() - timedelta(days=1))
        res = self.client.get(reverse("posts:view"), {"stage": "temp", "today": "1", "view": "one"})
        self.assertEqual([p.title for p in res.context["pl_items"]], ["오늘 글"])
        self.assertEqual(res.context["pl_tabs"][0]["count"], 1)
        self.assertContains(res, 'aria-pressed="true"')
        res = self.client.get(old.get_absolute_url(), {"stage": "temp", "today": "1"})
        self.assertEqual([p.title for p in res.context["pl_items"]], ["오늘 글"])
        self.assertIsNone(res.context["pl_current"])  # 조건에 안 맞는 글을 열어도 화면은 열린다

    def test_custom_filter(self):
        """[커스텀]: 일일루틴 하루 분량이 아닌 글만 (2026-10-22 사용자). 오늘 버튼 옆, 목록·글 보기 둘 다."""
        self.T.objects.create(title="루틴 글", stage="temp")
        self.N.objects.create(title="커스텀 네이버", stage="temp", custom=True)
        mine = self.T.objects.create(title="커스텀 글", stage="temp", custom=True)
        res = self.client.get(reverse("posts:view"), {"stage": "temp", "custom": "1", "view": "one"})
        self.assertEqual(sorted(p.title for p in res.context["pl_items"]), ["커스텀 글", "커스텀 네이버"])
        self.assertEqual(res.context["pl_tabs"][0]["count"], 2)
        self.assertIn("custom=1", res.context["pl_tabs"][1]["url"])  # 단계를 바꿔도 조건은 그대로
        self.assertContains(res, ">커스텀</a>")
        res = self.client.get(reverse("posts:view"), {"stage": "temp", "view": "list", "custom": "1"})
        self.assertEqual(sorted(p.title for p in res.context["posts"]), ["커스텀 글", "커스텀 네이버"])
        self.assertNotIn("custom", res.context["clear_url"])
        from apps.blog_types import transfer
        self.assertTrue(transfer.send(mine).custom)  # 상대 글쓰기로 보내도 커스텀

    def test_side_menu_has_collapse_button(self):
        res = self.client.get(reverse("posts:view"))
        self.assertContains(res, "data-nav-mini")
        self.assertContains(res, 'localStorage.getItem("nav.mini")')

    def test_posts_screen_merges_writers_and_filters_by_tree(self):
        self.T.objects.create(title="티 임시", stage="temp", bt_category=self.season.category)
        self.N.objects.create(title="네 임시", stage="temp")
        self.T.objects.create(title="티 검토", stage="review")
        url = reverse("posts:view")
        res = self.client.get(url, {"view": "one"})
        self.assertEqual(sorted(p.title for p in res.context["pl_items"]), ["네 임시", "티 임시"])
        self.assertEqual([t["count"] for t in res.context["pl_tabs"]], [2, 1])  # 임시글 · 검토글 (발행예정글·게시글 관리는 중메뉴로, 2026-10-23)
        res = self.client.get(url, {"sel": "u", "stage": "review", "view": "one"})
        self.assertEqual([p.title for p in res.context["pl_items"]], ["티 검토"])  # 미분류
        res = self.client.get(url, {"sel": self.season.category.sel, "view": "one"})
        self.assertEqual([p.title for p in res.context["pl_items"]], ["티 임시"])

    def test_bulk_move_and_send_mixed(self):
        t = self.T.objects.create(title="티", stage="temp")
        n = self.N.objects.create(title="네", stage="temp")
        self.client.post(reverse("posts:bulk"), {"ids": [f"tistory:{t.pk}", f"naver:{n.pk}"], "to": "review"})
        t.refresh_from_db(), n.refresh_from_db()
        self.assertEqual((t.stage, n.stage), ("review", "review"))
        self.client.post(reverse("posts:bulk"), {"ids": [f"tistory:{t.pk}"], "send": "1"})
        self.assertTrue(self.N.objects.filter(title="티", stage="temp").exists())

    def test_unclassified_node_and_place_from_class_side(self):
        p = self.T.objects.create(title="분류 없는 포스트", stage="post")
        java = SiteCategory.objects.get_or_create(blog=Blog.objects.get(name="memorily"), name="Java")[0]
        tree = self.client.get(INDEX).context["tree"]
        self.assertEqual(tree["unclassified"], 1)
        res = self.client.get(INDEX, {"sel": "u"})
        self.assertEqual([x.title for x in res.context["posts"]], ["분류 없는 포스트"])
        options = [pk for _, rows in res.context["posts"][0].site_groups for pk, _ in rows]
        self.assertIn(java.pk, options)
        self.assertIn(SiteCategory.objects.get(name="낙서장").pk, options)  # 모든 사이트
        back = f"{INDEX}?sel=u"
        res = self.client.post(reverse("blog_types:place_add"), {"site_category": java.pk, "post": f"tistory:{p.pk}", "next": back})
        self.assertRedirects(res, back, fetch_redirect_response=False)
        self.assertEqual(Placement.objects.get().tistory_post, p)

    def test_writer_pages_highlight_post_hub_menu(self):
        p = self.T.objects.create(title="글", stage="temp")
        res = self.client.get(p.get_absolute_url())
        self.assertEqual(res.context["ACTIVE_MENU"], "posts_view")  # 글 하나를 보는 화면은 '글 보기' 메뉴
        self.assertContains(res, f'{reverse("posts:view")}?stage=review&amp;view=one"')  # 단계 탭은 글 관리 안에서 (한 건씩 그대로)


class MappingPanesTests(TestCase):
    """카테고리 관리 오른쪽: 위 매핑 · 아래 글을 함께, 트리를 누르면 그 칸만"""

    def setUp(self):
        legacy_tree()
        user = get_user_model().objects.create_user("tester", password="pw-test-1234")
        self.client.force_login(user)
        from apps.writing.models import Post
        self.java = SiteCategory.objects.get_or_create(blog=Blog.objects.get(name="memorily"), name="Java")[0]
        self.post = Post.objects.create(title="자바 정리", stage="post")
        Placement.objects.create(site_category=self.java, tistory_post=self.post)

    def test_both_selections_at_once(self):
        res = self.client.get(INDEX, {"site": self.java.sel, "sel": "u"})
        self.assertEqual([p.post.title for p in res.context["placements"]], ["자바 정리"])  # 위
        self.assertEqual([p.title for p in res.context["posts"]], ["자바 정리"])  # 아래 (미분류)
        res = self.client.get(INDEX, {"sel": self.java.sel})  # 예전 주소도 위 칸으로
        self.assertEqual(res.context["site_sel"], self.java.sel)

    def test_partial_returns_only_that_pane(self):
        res = self.client.get(INDEX, {"site": self.java.sel}, HTTP_X_PARTIAL="top")
        self.assertTemplateUsed(res, "blog_types/_pane_top.html")
        self.assertTemplateNotUsed(res, "blog_types/index.html")
        self.assertContains(res, "자바 정리")
        res = self.client.get(INDEX, {"sel": "u"}, HTTP_X_PARTIAL="bottom")
        self.assertTemplateUsed(res, "blog_types/_pane_bottom.html")
        self.assertNotContains(res, "사이트 카테고리</span>")  # 트리는 다시 그리지 않는다

    def test_redirects_keep_the_other_selection(self):
        here = f"{INDEX}?site={self.java.sel}&sel=u"
        self.client.post(reverse("blog_types:add", args=["sitecat"]), {"name": "Spring", "parent": self.java.sel, "next": here})
        spring = SiteCategory.objects.get(name="Spring")
        res = self.client.post(reverse("blog_types:save", args=["sitecat", spring.pk]), {"name": "Spring Boot", "note": "", "next": here})
        self.assertRedirects(res, f"{INDEX}?site={spring.sel}&sel=u", fetch_redirect_response=False)
        res = self.client.get(INDEX, {"site": spring.sel, "sel": "u", "edit": spring.sel})
        self.assertIsNotNone(res.context["top_form"])
        self.assertIsNone(res.context["bottom_form"])


@override_settings(WRITING_DRAFTS_DIR=settings.BASE_DIR / "없는-원고-폴더")  # 저장소 원고를 글 관리로 가져오지 않게
class SitePublishTests(TestCase):
    """글 관리·글 보기의 사이트 고르기, 발행 완료 (한 건 · 일괄), 카테고리 관리 아래 목록의 조건 (2026-10-17 사용자)"""

    def setUp(self):
        legacy_tree()
        user = get_user_model().objects.create_user("tester", password="pw-test-1234")
        self.client.force_login(user)
        from apps.naver_writing.models import Post as NaverPost
        from apps.writing.models import Post
        self.T, self.N = Post, NaverPost
        self.java = SiteCategory.objects.get_or_create(blog=Blog.objects.get(name="memorily"), name="Java")[0]
        self.a = Post.objects.create(title="자바 정리", stage="post", target="memorily")
        self.b = NaverPost.objects.create(title="패딩 고르기", stage="post", target="black_lukey")
        self.pl = Placement.objects.create(site_category=self.java, tistory_post=self.a)

    def test_review_and_post_columns(self):
        r = self.T.objects.create(title="검토 중 글", stage="review", target="눈잎")
        res = self.client.get(reverse("posts:view"), {"stage": "review", "p": f"tistory:{r.pk}"})
        self.assertContains(res, 'action="/blog/posts/site/"')
        self.assertContains(res, f'value="tistory:{r.pk}"')
        self.assertContains(res, '<option value="눈잎" selected>눈잎</option>', html=False)
        self.assertNotContains(res, "검토 완료")  # 검토 칸 대신 사이트
        self.assertContains(res, "카테고리 고르기")  # 검토글에서도 카테고리에 넣는다 (2026-10-22)
        res = self.client.get(reverse("posts:view"), {"stage": "post"})
        for th in ["사이트", "카테고리", "변환", "발행"]:
            self.assertContains(res, f">{th}</th>", html=False)
        self.assertNotContains(res, ">타겟</th>", html=False)
        self.assertContains(res, "memorily › Java")
        self.assertContains(res, 'name="publish" value="done"')  # 체크한 것을 발행 완료

    def test_pick_site(self):
        nxt = reverse("posts:view") + "?stage=review"
        res = self.client.post(reverse("posts:site"), {"ids": f"naver:{self.b.pk}", "site": "눈잎", "next": nxt})
        self.assertRedirects(res, nxt, fetch_redirect_response=False)
        self.b.refresh_from_db()
        self.assertEqual(self.b.target, "눈잎")
        self.client.post(reverse("posts:site"), {"ids": f"naver:{self.b.pk}", "site": "없는 사이트"})
        self.b.refresh_from_db()
        self.assertEqual(self.b.target, "눈잎")  # 운영 목록에 있는 사이트만
        self.client.post(reverse("posts:site"), {"ids": [f"naver:{self.b.pk}", f"tistory:{self.a.pk}"], "site": ""})
        self.a.refresh_from_db()
        self.assertEqual(self.a.target, "")

    def test_publish_one_and_bulk_moves_placements_too(self):
        self.client.post(reverse("writing:status", args=[self.a.pk]), {"field": "publish_status", "value": "done"})
        self.a.refresh_from_db()
        self.pl.refresh_from_db()
        self.assertEqual((self.a.publish_status, self.pl.status), ("done", "published"))
        temp = self.T.objects.create(title="임시", stage="temp")
        self.client.post(reverse("posts:bulk"), {"ids": [f"tistory:{self.a.pk}", f"naver:{self.b.pk}", f"tistory:{temp.pk}"],
                                                  "publish": "todo"})
        self.a.refresh_from_db()
        self.pl.refresh_from_db()
        self.assertEqual((self.a.publish_status, self.pl.status), ("todo", "unsaved"))
        self.client.post(reverse("posts:bulk"), {"ids": [f"tistory:{self.a.pk}", f"naver:{self.b.pk}", f"tistory:{temp.pk}"],
                                                  "publish": "done"})
        self.b.refresh_from_db()
        temp.refresh_from_db()
        self.assertEqual((self.b.publish_status, temp.publish_status), ("done", "todo"))  # 발행예정글만

    def test_view_shows_site_and_placements(self):
        res = self.client.get(reverse("posts:view"), {"stage": "post", "p": f"tistory:{self.a.pk}"})
        self.assertContains(res, "사이트 고르기")
        self.assertContains(res, "memorily › Java")
        self.assertContains(res, "미변환")

    def test_mapping_bottom_filters(self):
        self.T.objects.create(title="임시 글", stage="temp")
        res = self.client.get(INDEX)
        self.assertEqual(sorted(p.title for p in res.context["posts"]), ["자바 정리", "패딩 고르기"])  # 발행예정글만
        self.assertContains(res, "<th style=\"width:76px\">사이트</th><th style=\"width:21%\">넣은 곳 · 변환</th><th style=\"width:140px\">발행</th>", html=False)
        res = self.client.get(INDEX, {"psite": "black_lukey"})
        self.assertEqual([p.title for p in res.context["posts"]], ["패딩 고르기"])
        self.assertEqual(res.context["posts"][0].site_groups[0][0], "black_lukey")  # 그 글의 사이트 카테고리가 위
        self.T.objects.filter(pk=self.a.pk).update(target="")
        self.assertEqual([p.title for p in self.client.get(INDEX, {"psite": "-"}).context["posts"]], ["자바 정리"])
        from datetime import timedelta

        from django.utils import timezone
        self.N.objects.filter(pk=self.b.pk).update(created_at=timezone.now() - timedelta(days=2))
        res = self.client.get(INDEX, {"today": "1"})
        self.assertEqual([p.title for p in res.context["posts"]], ["자바 정리"])
        self.assertContains(res, "today=1")
        res = self.client.get(INDEX, {"site": self.java.sel})
        self.assertContains(res, ">미발행</button>", html=False)
        self.assertContains(res, ">발행 완료</button>", html=False)
        self.assertNotContains(res, "임시저장")

    def test_post_tab_flat_sorted_and_publish_filter(self):
        """발행예정글 (2026-10-21 사용자): 분류 트리·분류 줄 없이, 미발행이 위 → 최신 순, 발행 전체/미발행/발행 완료 조건"""
        from datetime import timedelta

        from django.utils import timezone
        old = self.T.objects.create(title="오래된 미발행", stage="post")
        done = self.T.objects.create(title="발행한 글", stage="post", publish_status="done")
        self.T.objects.filter(pk=old.pk).update(created_at=timezone.now() - timedelta(days=3))
        self.N.objects.filter(pk=self.b.pk).update(created_at=timezone.now() - timedelta(days=1))
        url = reverse("posts:view")
        res = self.client.get(url, {"stage": "post", "sel": "u"})
        self.assertEqual([p.title for p in res.context["posts"]], ["자바 정리", "패딩 고르기", "오래된 미발행"])  # 발행 완료는 게시글 관리
        self.assertEqual(res.context["sel"], "")  # 분류 조건은 쓰지 않는다
        self.assertNotContains(res, 'data-bt-tree="class"')
        self.assertNotContains(res, 'class="wr-group"')
        self.assertContains(res, "bt-layout-1")
        # 게시글 관리 (2026-10-23 사용자): 글 관리 탭에서 빼 중메뉴로. 예전 주소는 그리로
        self.assertEqual([t["label"] for t in res.context["tabs"]], ["임시글", "검토글", "발행예정글"])
        self.assertRedirects(self.client.get(url, {"stage": "done"}), reverse("posts:published"), fetch_redirect_response=False)
        res = self.client.get(reverse("posts:published"))
        self.assertEqual([p.title for p in res.context["posts"]], ["발행한 글"])
        self.assertContains(res, "wr-compact")  # 발행예정글과 같은 표
        view = self.client.get(url, {"p": f"tistory:{done.pk}"})
        self.assertEqual(view.context["pl_stage"], "done")  # 글 보기 왼쪽 목록도 게시글 관리
        self.T.objects.create(title="임시", stage="temp")
        res = self.client.get(url, {"stage": "temp", "view": "one"})
        self.assertContains(res, 'data-bt-tree="list"')  # 다른 단계는 한 건씩 (왼쪽은 글 목록)

    def test_mapping_list_hides_published_and_converted_newest_first(self):
        """카테고리 관리 아래 목록 (2026-10-21 사용자): 발행 완료·변환 완료 글은 빼고 최신 순"""
        from datetime import timedelta

        from django.utils import timezone
        self.N.objects.filter(pk=self.b.pk).update(created_at=timezone.now() - timedelta(days=1))
        conv = self.T.objects.create(title="변환 끝난 글", stage="post")
        Placement.objects.create(site_category=self.java, tistory_post=conv, convert_status="checked")
        self.T.objects.create(title="발행한 글", stage="post", publish_status="done")
        half = self.T.objects.create(title="한 곳만 변환", stage="post")
        Placement.objects.create(site_category=self.java, tistory_post=half, convert_status="done")
        Placement.objects.create(site_category=SiteCategory.objects.get(name="낙서장"), tistory_post=half)
        res = self.client.get(INDEX)
        self.assertEqual([p.title for p in res.context["posts"]], ["한 곳만 변환", "자바 정리", "패딩 고르기"])

    def test_post_grid_category_picker_places_post(self):
        """글 관리·글 보기 발행예정글 (2026-10-21 사용자): 카테고리 칸에서 바로 사이트 카테고리에 넣는다"""
        res = self.client.get(reverse("posts:view"), {"stage": "post"})
        self.assertContains(res, "wr-compact")
        row = next(p for p in res.context["posts"] if p.pk == self.b.pk and p.writer == "naver")  # 두 표의 pk 가 겹친다
        self.assertEqual(row.site_groups[0][0], "black_lukey")  # 그 글의 사이트가 위
        self.assertContains(res, f'<input type="hidden" name="post" value="naver:{self.b.pk}">', html=False)
        lukey = SiteCategory.objects.get(name="낙서장")
        back = reverse("posts:view") + "?stage=post"
        res = self.client.post(reverse("blog_types:place_add"), {"post": f"naver:{self.b.pk}", "site_category": lukey.pk, "next": back})
        self.assertRedirects(res, back, fetch_redirect_response=False)
        self.assertTrue(Placement.objects.filter(naver_post=self.b, site_category=lukey).exists())

    def test_convert_panel_and_review_convert(self):
        """글 관리 (2026-10-22 사용자): 발행예정글 줄을 누르면 아래에 변환 칸, 변환·전체 변환 버튼, 검토글도 넣고 변환"""
        from apps.core.models import ROUTINE_BRIEF_TOKEN_KEY, AppSetting
        res = self.client.get(reverse("posts:view"), {"stage": "post"})
        self.assertContains(res, f'href="{reverse("site_templates:post")}?p=tistory:{self.a.pk}&amp;back=')  # 제목 → 변환 화면
        self.assertNotContains(res, "data-cv-panel")  # 줄을 눌러 펼치지 않는다
        self.assertContains(res, "data-trash-norow")  # 줄마다 휴지통 없이, 체크하고 위 '삭제'
        self.assertNotContains(res, "체크한 것을")
        self.assertNotContains(res, 'id="rc-note"')  # 재변환 코멘트는 뺐다 (2026-10-23 사용자)
        self.assertContains(res, "data-feeds-check")  # 갱신: 사이트에 올라온 글로 발행 완료
        # 2026-10-28 사용자: 줄마다 '변환·다시' 버튼 대신 체크하고 위 '변환' — 줄 체크박스가 넣은 곳 번호를 든다
        self.assertNotContains(res, f'data-st-run="{self.pl.pk}"')
        self.assertContains(res, f'data-cv="{self.pl.pk},"')
        self.assertContains(res, 'data-st-checked="ids"')
        self.assertNotContains(res, "전체 변환")
        page = self.client.get(reverse("site_templates:post"), {"p": f"tistory:{self.a.pk}", "back": "/blog/posts/view/?stage=post"})
        self.assertEqual(page.context["ACTIVE_MENU"], "posts_view")
        self.assertContains(page, "아직 변환본이 없습니다")
        self.assertContains(page, 'href="/blog/posts/view/?stage=post"')  # 글 관리로 돌아가기
        nocat = self.client.get(reverse("site_templates:post"), {"p": f"naver:{self.b.pk}"})
        self.assertContains(nocat, "카테고리 고르기")  # 넣은 곳이 없으면 여기서 바로 넣는다
        self.assertNotContains(res, f'data-href="{self.a.get_absolute_url()}')
        panel = self.client.get(reverse("site_templates:panel"), {"p": f"tistory:{self.a.pk}", "next": "/blog/posts/view/?stage=post"})
        self.assertContains(panel, "원문")
        self.assertContains(panel, "아직 변환본이 없습니다")  # 변환 전이면 변환본은 비어 있다
        self.assertContains(panel, f'id="st-request-{self.pl.pk}"')
        self.assertContains(panel, '<input type="hidden" name="next" value="/blog/posts/view/?stage=post">', html=False)
        empty = self.client.get(reverse("site_templates:panel"), {"p": f"naver:{self.b.pk}"})
        self.assertContains(empty, "아직 카테고리에 넣지 않았습니다")
        # 검토글: 카테고리에 넣고 변환할 수 있다
        r = self.T.objects.create(title="검토 중 글", stage="review", target="memorily")
        back = reverse("posts:view") + f"?stage=review&p=tistory:{r.pk}"
        self.client.post(reverse("blog_types:place_add"), {"post": f"tistory:{r.pk}", "site_category": self.java.pk, "next": back})
        rpl = Placement.objects.get(tistory_post=r)
        res = self.client.get(back)
        self.assertContains(res, f'data-st-run="{rpl.pk}"')
        self.assertContains(res, "원문 ↔ 변환본 보기")
        AppSetting.set(ROUTINE_BRIEF_TOKEN_KEY, "tok")
        data = self.client.post(reverse("site_templates:run"), {"ids": str(rpl.pk)}).json()
        self.assertTrue(data["prompt"].startswith("# 사이트 변환"))
        # 변환 칸에서 저장하면 그 목록으로 돌아간다
        res = self.client.post(reverse("site_templates:convert", args=[rpl.pk]), {
            "action": "save", "converted_title": "t", "converted_body": "b", "convert_note": "", "converted_tags": "",
            "converted_check": "", "next": back})
        self.assertRedirects(res, back, fetch_redirect_response=False)


class SimpleClassesTests(TestCase):
    """0017: 글 분류를 '사이트 > 고정 소재' 로 줄임 (2026-10-22 사용자). 옛 분류는 휴지통, 글은 가까운 새 소재로."""

    def test_new_tree_and_old_in_trash(self):
        from apps.core.models import TrashEntry
        self.assertEqual(list(Section.objects.values_list("name", flat=True)), ["눈잎", "black_lukey", "밤밤", "memorily", "워드프레스"])  # memorily › AI 는 0021, 워드프레스 0030
        self.assertEqual(list(Category.objects.filter(section__name="밤밤").values_list("name", flat=True)),
                         ["코스피 시황 노트", "나스닥 시황 노트", "해외 여행"])  # 해외 여행은 눈잎에서 옮겨 옴 (routines 0020), 제품소개 지움 (0028), 시황 노트를 코스피·나스닥으로 다시 나눔 (0033)
        self.assertFalse(Category.objects.filter(name="그 외").exists())  # '그 외'는 없다 (밤밤 0028 · 눈잎·black_lukey routines 0022 에서 뺌)
        self.assertFalse(PostType.objects.exists())  # 소분류 없이 소재만
        self.assertTrue(Category.objects.get(name="코스피 시황 노트").direction)  # 방향 = 글쓰기 컨셉
        trashed = TrashEntry.objects.filter(model_label="blog_types.section")
        self.assertEqual(sorted(trashed.values_list("title", flat=True)), ["IT/AI", "광고 수익 (조회수)", "판매 수익 (커넥트)"])
        self.assertIn("blog_types.subtype", trashed.get(title="판매 수익 (커넥트)").members)  # 복원하면 아래까지 함께

    def test_posts_move_to_new_keyword(self):
        from importlib import import_module

        from django.apps import apps as django_apps

        from apps.writing.models import Post
        legacy_tree()
        old = Category.objects.get(name="여행·체험")
        post = Post.objects.create(title="경주 당일치기", bt_category=old, bt_type=old.types.first())
        import_module("apps.blog_types.migrations.0017_simple_classes").forward(django_apps, None)
        post.refresh_from_db()
        self.assertEqual((post.bt_category.section.name, post.bt_category.name, post.bt_type), ("black_lukey", "지역 놀거리", None))
        self.assertEqual(Section.objects.count(), 3)

    def test_draft_line_with_old_style_depth_finds_keyword(self):
        from apps.writing import drafts
        from apps.writing.models import Post
        from apps.writing.views import _classify_draft
        d = drafts.parse("분류: 눈잎 > 공모주 > 일정 달력\n<!-- 본문 시작 -->\n# 공모주\n본문\n<!-- 본문 끝 -->\n", "T1_공모주")
        post = Post(title=d.title)
        _classify_draft(post, d)
        self.assertEqual(post.bt_category.name, "공모주")


@override_settings(WRITING_DRAFTS_DIR=settings.BASE_DIR / "없는-원고-폴더")
class TempPostsTests(TestCase):
    """임시글 (2026-10-22 사용자): 커스텀·그날 글 말고는 휴지통으로 정리, 왼쪽 목록은 사이트별로."""

    def test_old_temp_posts_go_to_trash(self):
        from datetime import datetime
        from importlib import import_module

        from django.apps import apps as django_apps
        from django.utils import timezone

        from apps.core.models import TrashEntry
        from apps.naver_writing.models import Post as NaverPost
        from apps.writing.models import Post
        old, today = timezone.make_aware(datetime(2026, 10, 20, 9)), timezone.make_aware(datetime(2026, 10, 22, 10))
        for model, title, when, extra in [(Post, "옛 임시글", old, {}), (Post, "옛 커스텀", old, {"custom": True}),
                                          (Post, "오늘 글", today, {}), (NaverPost, "옛 검토글", old, {"stage": "review"}),
                                          (NaverPost, "옛 네이버 임시글", old, {})]:
            post = model.objects.create(title=title, **extra)
            model.objects.filter(pk=post.pk).update(created_at=when)
        import_module("apps.writing.migrations.0017_clear_old_temp").forward(django_apps, None)
        self.assertEqual(set(Post.objects.values_list("title", flat=True)), {"옛 커스텀", "오늘 글"})
        self.assertEqual(set(NaverPost.objects.values_list("title", flat=True)), {"옛 검토글"})
        self.assertEqual(TrashEntry.objects.filter(model_label__in=["writing.post", "naver_writing.post"]).count(), 2)

    def test_temp_list_grouped_by_site(self):
        from apps.writing.models import Post
        self.client.force_login(get_user_model().objects.create_user("tester", password="pw-test-1234"))
        for title, site in [("밤밤 글", "밤밤"), ("사이트 없는 글", ""), ("눈잎 글", "눈잎"), ("눈잎 새 글", "눈잎")]:
            Post.objects.create(title=title, target=site)
        res = self.client.get(reverse("posts:view"), {"stage": "temp", "view": "list"})
        self.assertEqual([p.title for p in res.context["posts"]], ["눈잎 새 글", "눈잎 글", "밤밤 글", "사이트 없는 글"])
        one = self.client.get(reverse("posts:view"), {"stage": "temp", "p": f"tistory:{Post.objects.first().pk}"})
        self.assertContains(one, '<div class="pl-group"><span>눈잎</span><span class="cnt">2</span></div>', count=1)


class SiteCleanupTests(TestCase):
    """0018 (2026-10-22 사용자): AI 소식은 커스텀 고정 주제(memorily), 글 사이트·분류 바로잡기, memorily 에러 글은 휴지통."""

    def test_ai_news_is_custom_topic_on_memorily(self):
        from apps.routines.models import FixedTopic
        topic = FixedTopic.objects.get(name="AI 소식")
        self.assertEqual((topic.site, topic.per_week), ("memorily", 1))  # 한 번에 1편 (routines 0017)
        self.assertTrue(topic.note.startswith("한 번에 한 편"))
        self.assertIn("설명할 가치가 없는 업그레이드", topic.note)
        self.assertFalse(Category.objects.filter(name="AI 소식").exists())
        self.assertNotIn("AI", Blog.objects.get(name="black_lukey").content)
        self.client.force_login(get_user_model().objects.create_user("tester", password="pw-test-1234"))
        res = self.client.get(reverse("routines:topics"))
        self.assertContains(res, f'<td class="tp-note" data-tp-edit="{topic.pk}"')  # 지침 칸을 누르면 전체가 보이는 고치기 칸이 열린다
        self.assertNotContains(res, "주 1편</option>")  # 주당 편수는 뺐다 — 실행할 때 줄마다 편수 (2026-10-23 사용자)

    def test_posts_get_new_site_and_error_post_goes_to_trash(self):
        from importlib import import_module

        from django.apps import apps as django_apps

        from apps.naver_writing.models import Post as NaverPost
        from apps.writing.models import Post
        mig = import_module("apps.blog_types.migrations.0018_site_cleanup")
        bam = Section.objects.get(name="밤밤")  # 0028 이 지운 옛 소재를 다시 두고 0018 을 돌린다
        Category.objects.create(section=bam, code="X", name="코스피")
        Category.objects.create(section=bam, code="Y", name="상품 추천")
        kospi = Post.objects.create(title="코스피 3.29% 반등 다음 날 다시 약세, 9거래일 종가표로 보는 지금 위치", target="눈잎")
        heat = NaverPost.objects.create(title="전기장판 vs 온수매트 vs 탄소매트, 월 전기료 직접 계산하고 고르기 (2026 겨울)", target="black_lukey")
        anime = Post.objects.create(title="나루토 회차정리 애니만화 환산기 명장면 등 모음", target="memorily",
                                    bt_category=Category.objects.create(section=Section.objects.get(name="눈잎"), code="Z", name="그 외"))  # routines 0022 가 지운 것을 다시
        err = Post.objects.create(title=mig.TRASH_TITLES[0], target="memorily")
        mig.forward(django_apps, None)
        kospi.refresh_from_db(), heat.refresh_from_db(), anime.refresh_from_db()
        self.assertEqual((kospi.target, kospi.bt_category.name), ("밤밤", "코스피"))
        self.assertEqual((heat.target, heat.bt_category.section.name, heat.bt_category.name), ("밤밤", "밤밤", "상품 추천"))
        self.assertEqual((anime.target, anime.bt_category), ("memorily", None))
        self.assertFalse(Post.objects.filter(pk=err.pk).exists())
        self.assertTrue(Post.all_objects.filter(pk=err.pk, deleted_at__isnull=False).exists())


class NunipSiteCategoryTests(TestCase):
    """0019: 눈잎 사이트 카테고리 = 티스토리 관리 화면 그대로, 순서도 (2026-10-22 사용자)."""
    NAMES = ["청년·신혼 정책", "주택 공고", "공모주", "해외 여행", "일본 여행", "일상", "생활"]  # 생활 (0040)

    def site_names(self):
        return list(SiteCategory.objects.filter(blog__name="눈잎", parent=None).order_by("order", "pk").values_list("name", flat=True))

    def test_seeded_in_tistory_order(self):
        self.assertEqual(self.site_names(), self.NAMES)
        self.assertEqual(SiteCategory.objects.get(blog__name="눈잎", name="공모주").note, "티스토리 주제: 경제")
        self.assertEqual(list(Category.objects.filter(section__name="눈잎").values_list("name", flat=True)),
                         ["청년·신혼 정책", "주택 공고", "공모주", "일본", "생활"])  # 그 외는 뺌 (routines 0022), 일본 하나로, 해외 여행은 밤밤 (routines 0020), 동물 (0028)

    def test_life_category(self):
        """0040 (2026-10-27 사용자): 독감 무료접종 같은 공공 일정을 눈잎 › 생활로. 그 외 앞, 사이트 카테고리에 글 모양"""
        life = Category.objects.get(section__name="눈잎", name="생활")
        self.assertEqual(life.code, "E")  # 그 외(F)는 routines 0022 에서 뺌
        self.assertIn("무료 접종", life.direction)
        self.assertIn("독감 무료접종 일정", SiteCategory.objects.get(blog__name="눈잎", name="생활").concept)
        self.assertIn("생활(", Blog.objects.get(name="눈잎").content)

    def test_extra_categories_trashed_unless_they_hold_posts(self):
        from importlib import import_module

        from django.apps import apps as django_apps

        from apps.writing.models import Post
        nunip = Blog.objects.get(name="눈잎")
        empty = SiteCategory.objects.create(blog=nunip, name="빈 메뉴", order=0)
        used = SiteCategory.objects.create(blog=nunip, name="쓰는 메뉴", order=0)
        Placement.objects.create(site_category=used, tistory_post=Post.objects.create(title="넣은 글"))
        SiteCategory.objects.filter(name="공모주").update(order=99)
        import_module("apps.blog_types.migrations.0019_nunip_site_categories").forward(django_apps, None)
        self.assertEqual(self.site_names(), self.NAMES[:-1] + ["쓰는 메뉴"])  # 0019 를 다시 돌리면 그 뒤에 더한 빈 생활도 걷힌다
        self.assertTrue(SiteCategory.all_objects.filter(pk=empty.pk, deleted_at__isnull=False).exists())


class TrimAiNewsTests(TestCase):
    """writing 0018 (2026-10-22 사용자): AI 소식 6편 중 가장 최근 T108 만 남기고 5편은 휴지통."""

    def test_only_latest_ai_news_stays(self):
        from importlib import import_module

        from django.apps import apps as django_apps

        from apps.writing.models import Post
        mig = import_module("apps.writing.migrations.0018_trim_ai_news")
        old = [Post.objects.create(title=t, custom=True) for t in mig.TITLES]
        keep = Post.objects.create(title="시리 AI 한국어가 iOS 27.2 RC에 들어왔고, 윈도우는 Copilot 진입점을 줄입니다 (AI 소식 10-22)", custom=True)
        mig.forward(django_apps, None)
        self.assertEqual(list(Post.objects.values_list("pk", flat=True)), [keep.pk])
        self.assertEqual(Post.all_objects.filter(pk__in=[p.pk for p in old], deleted_at__isnull=False).count(), 5)


class WordpressAsofLineTests(TestCase):
    """blog_types 0048 (2026-10-28 사용자): 워드프레스 글 끝 'YYYY-MM-DD 기준, 바뀌면 고칩니다.' 줄을 규칙·원고·변환본에서 지운다."""

    def test_line_dropped(self):
        from importlib import import_module

        from django.apps import apps as django_apps

        from apps.writing.models import Post
        wp = Blog.objects.get(platform="wordpress")
        car = SiteCategory.objects.create(blog=wp, name="시험 자동차",
                                          concept="공통: 본문 → `참고:` 출처(기관·문서·날짜) → 기준일 줄('2026-10-26 기준, 바뀌면 고칩니다').\n둘째 줄")
        post = Post.objects.create(title="겨울 점검", body="본문\r\n\r\n참고: 가 (https://a.com)\r\n\r\n2026-10-26 기준, 바뀌면 고칩니다.\r\n<!-- 본문 끝 -->")
        md = Placement.objects.create(site_category=car, tistory_post=post, converted_body="본문\n\n참고: 가\n\n2026-10-27 기준, 바뀌면 고칩니다.")
        html = Placement.objects.create(site_category=car, tistory_post=post,
                                        converted_body="<p>본문</p>\n<p>참고: 가</p>\n<p>2026-10-28 기준, 바뀌면 고칩니다.</p>")
        tistory = Placement.objects.create(site_category=SiteCategory.objects.create(blog=Blog.objects.get(platform="tistory", name="눈잎"), name="시험"),
                                           tistory_post=post, converted_body="끝\n\n2026-10-26 기준, 바뀌면 고칩니다.")
        import_module("apps.blog_types.migrations.0048_wordpress_drop_asof_line").forward(django_apps, None)
        for o in (car, post, md, html, tistory):
            o.refresh_from_db()
        self.assertEqual(car.concept, "공통: 본문 → `참고:` 출처(기관·문서·날짜).\n둘째 줄")
        self.assertEqual(post.body, "본문\r\n\r\n참고: 가 (https://a.com)\r\n<!-- 본문 끝 -->")
        self.assertEqual(md.converted_body, "본문\n\n참고: 가")
        self.assertEqual(html.converted_body, "<p>본문</p>\n<p>참고: 가</p>")
        self.assertIn("바뀌면 고칩니다", tistory.converted_body)  # 워드프레스만
        self.assertEqual(md.changed_at, None)  # 발행 글은 PC 가 REST 로 고쳤다 — '수정됨' 불은 켜지 않는다


@override_settings(WRITING_DRAFTS_DIR=settings.BASE_DIR / "없는-원고-폴더")
class PostPlanTests(TestCase):
    """발행예정글 (2026-10-22 사용자): 사이트로 거르고, 줄마다 발행 예정일을 정해 그 순서로 본다."""

    def setUp(self):
        self.client.force_login(get_user_model().objects.create_user("tester", password="pw-test-1234"))

    def test_site_filter_and_planned_date_order(self):
        from datetime import date

        from apps.naver_writing.models import Post as NaverPost
        from apps.writing.models import Post
        a = Post.objects.create(title="날짜 없는 글", stage="post", target="눈잎")
        b = NaverPost.objects.create(title="25일 글", stage="post", target="black_lukey")
        c = Post.objects.create(title="24일 글", stage="post", target="눈잎")
        url = reverse("posts:view")
        for post, day in ((b, "2026-10-25"), (c, "2026-10-24")):
            self.client.post(reverse("posts:plan"), {"post": f"{'naver' if post is b else 'tistory'}:{post.pk}", "day": day, "next": url})
        c.refresh_from_db()
        self.assertEqual(c.planned_on, date(2026, 10, 24))
        res = self.client.get(url, {"stage": "post"})
        self.assertEqual([p.title for p in res.context["posts"]], ["24일 글", "25일 글", "날짜 없는 글"])  # 예정일 순, 없는 글은 끝
        self.assertContains(res, 'name="day" value="2026-10-24"')
        res = self.client.get(url, {"stage": "post", "site": "눈잎"})
        self.assertEqual([p.title for p in res.context["posts"]], ["24일 글", "날짜 없는 글"])
        self.assertContains(res, '<option value="눈잎" selected>눈잎</option>', html=False)
        self.client.post(reverse("posts:plan"), {"post": f"tistory:{c.pk}", "day": "", "next": url})  # 지우기
        c.refresh_from_db()
        self.assertIsNone(c.planned_on)
        self.assertEqual(self.client.get(url, {"stage": "post", "site": "없는 사이트"}).context["site_filter"], "")
        a.delete()


@override_settings(WRITING_DRAFTS_DIR=settings.BASE_DIR / "없는-원고-폴더")
class PostCategoryEditTests(TestCase):
    """발행예정글 (2026-10-22 사용자): 예정일 → 사이트 순, '카테고리 수정'으로 넣은 카테고리를 바꾼다."""

    def setUp(self):
        self.client.force_login(get_user_model().objects.create_user("tester", password="pw-test-1234"))

    def test_order_by_date_then_site(self):
        from datetime import date

        from apps.writing.models import Post
        day = date(2026, 10, 24)
        for title, site, planned in [("밤밤 24일", "밤밤", day), ("눈잎 24일", "눈잎", day), ("눈잎 날짜 없음", "눈잎", None),
                                     ("memorily 25일", "memorily", date(2026, 10, 25))]:
            Post.objects.create(title=title, stage="post", target=site, planned_on=planned)
        res = self.client.get(reverse("posts:view"), {"stage": "post"})
        self.assertEqual([p.title for p in res.context["posts"]], ["눈잎 24일", "밤밤 24일", "memorily 25일", "눈잎 날짜 없음"])
        self.assertContains(res, "data-cat-edit")

    def test_move_placement_to_other_category(self):
        from apps.writing.models import Post
        post = Post.objects.create(title="옮길 글", stage="post", target="눈잎")
        old = SiteCategory.objects.get(blog__name="눈잎", name="공모주")
        same_site = SiteCategory.objects.get(blog__name="눈잎", name="주택 공고")
        other_site = SiteCategory.objects.get(blog__name="black_lukey", name="낙서장")
        pl = Placement.objects.create(site_category=old, tistory_post=post, convert_status="done")
        res = self.client.get(reverse("posts:view"), {"stage": "post"})
        self.assertContains(res, f'action="{reverse("blog_types:place_move", args=[pl.pk])}"')
        self.assertContains(res, f'<option value="{old.pk}" selected>눈잎 › 공모주</option>', html=False)
        self.client.post(reverse("blog_types:place_move", args=[pl.pk]), {"site_category": same_site.pk})
        pl.refresh_from_db()
        self.assertEqual((pl.site_category, pl.convert_status), (same_site, "done"))  # 같은 사이트면 변환본 그대로
        self.client.post(reverse("blog_types:place_move", args=[pl.pk]), {"site_category": other_site.pk})
        pl.refresh_from_db()
        self.assertEqual((pl.site_category, pl.convert_status), (other_site, "none"))  # 다른 사이트면 다시 변환


@override_settings(WRITING_DRAFTS_DIR=settings.BASE_DIR / "없는-원고-폴더")
class PostPlanSplitTests(TestCase):
    """발행예정글 (2026-10-22 사용자): 예정일 없음(위 7) · 정함(아래 3) 두 표, 체크한 글에 예정일 한꺼번에."""

    def setUp(self):
        self.client.force_login(get_user_model().objects.create_user("tester", password="pw-test-1234"))

    def test_two_grids_and_bulk_plan(self):
        from datetime import date

        from django.utils import timezone

        from apps.naver_writing.models import Post as NaverPost
        from apps.writing.models import Post
        a = Post.objects.create(title="가", stage="post", target="눈잎")
        b = NaverPost.objects.create(title="나", stage="post", target="밤밤")
        c = Post.objects.create(title="다", stage="post", target="눈잎", planned_on=date(2026, 10, 30))
        url = reverse("posts:view")
        res = self.client.get(url, {"stage": "post"})
        self.assertEqual(([p.title for p in res.context["unplanned"]], [p.title for p in res.context["planned"]]), (["가", "나"], ["다"]))
        self.assertContains(res, "발행 예정일 없음")
        self.assertContains(res, 'name="plan" value="1"')
        self.client.post(reverse("posts:bulk"), {"ids": [f"tistory:{a.pk}", f"naver:{b.pk}"], "plan": "1", "plan_day": "2026-10-28", "next": url})
        a.refresh_from_db(), b.refresh_from_db()
        self.assertEqual((a.planned_on, b.planned_on), (date(2026, 10, 28), date(2026, 10, 28)))
        res = self.client.get(url, {"stage": "post"})
        self.assertEqual([p.title for p in res.context["planned"]], ["가", "나", "다"])  # 날짜 → 사이트(눈잎 · 밤밤) 순
        self.client.post(reverse("posts:bulk"), {"ids": [f"tistory:{c.pk}"], "plan": "1", "plan_day": "", "next": url})
        c.refresh_from_db()
        self.assertEqual(c.planned_on, timezone.localdate())  # 날짜를 안 고르면 오늘 (2026-10-28 사용자)
        self.client.post(reverse("posts:plan"), {"post": f"tistory:{c.pk}", "day": ""})
        c.refresh_from_db()
        self.assertIsNone(c.planned_on)  # 지우기는 줄의 날짜 칸을 비워서


@override_settings(WRITING_DRAFTS_DIR=settings.BASE_DIR / "없는-원고-폴더")
class PostMenusTests(TestCase):
    """2026-10-23 사용자: 글 관리 아래 중메뉴 발행예정글(크게) · 게시글 관리(발행 완료), 발행예정글 '갱신', 위쪽 바로가기."""

    def setUp(self):
        from apps.naver_writing.models import Post as NaverPost
        from apps.writing.models import Post
        self.client.force_login(get_user_model().objects.create_user("tester", password="pw-test-1234"))
        self.T, self.N = Post, NaverPost

    def test_planned_menu_page(self):
        from django.utils import timezone
        today = timezone.localdate()
        self.T.objects.create(title="날짜 없음", stage="post", target="눈잎")
        self.T.objects.create(title="오늘 쓸 글", stage="post", target="눈잎", planned_on=today)
        self.N.objects.create(title="오늘 쓸 네이버", stage="post", target="black_lukey", planned_on=today)
        self.T.objects.create(title="발행한 글", stage="post", publish_status="done")
        res = self.client.get(reverse("posts:planned"))
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context["ACTIVE_MENU"], "posts_planned")
        self.assertEqual([p.title for p in res.context["unplanned"]], ["날짜 없음"])
        self.assertEqual([p.title for p in res.context["planned"]], ["오늘 쓸 글", "오늘 쓸 네이버"])
        self.assertEqual(res.context["planned"][0].day_head["count"], 2)  # 날짜 묶음 머리
        self.assertContains(res, "wr-day-row is-today")
        self.assertContains(res, "data-pp-split")  # 두 표 + 높이 손잡이
        # 예정일 없는 글은 작성일로 묶는다 (2026-10-27 사용자). 최근 날이 위, 작성일에는 '지남'을 달지 않는다
        from datetime import timedelta
        old = self.T.objects.create(title="그제 쓴 글", stage="post", target="눈잎")
        self.T.objects.filter(pk=old.pk).update(created_at=timezone.now() - timedelta(days=2))
        res = self.client.get(reverse("posts:planned"))
        top = res.context["unplanned"]
        self.assertEqual([p.title for p in top], ["날짜 없음", "그제 쓴 글"])
        self.assertEqual((top[0].day_head["today"], top[1].day_head["day"], top[1].day_head["past"]),
                         (True, today - timedelta(days=2), False))
        self.assertContains(res, "data-feeds-check")  # 갱신
        self.assertContains(res, ">예정일</button>", html=False)  # 짧은 버튼
        self.assertNotContains(res, "예정일 주기")
        self.assertNotContains(res, "재변환")
        res = self.client.get(reverse("posts:planned"), {"site": "black_lukey"})
        self.assertEqual([p.title for p in res.context["posts"]], ["오늘 쓸 네이버"])

    def test_published_menu_sorted_site_category_date(self):
        from datetime import timedelta

        from django.utils import timezone
        today = timezone.localdate()
        java = SiteCategory.objects.create(blog=Blog.objects.get(name="memorily"), name="자바", order=2)
        vue = SiteCategory.objects.create(blog=Blog.objects.get(name="memorily"), name="뷰", order=1)

        def done(title, target, days, cat=None):
            post = self.T.objects.create(title=title, stage="post", target=target, publish_status="done",
                                         published_on=today - timedelta(days=days))
            if cat:
                Placement.objects.create(site_category=cat, tistory_post=post, status="published")
            return post
        done("눈잎 글", "눈잎", 0)
        done("자바 옛글", "memorily", 3, java)
        done("자바 새글", "memorily", 1, java)
        done("뷰 글", "memorily", 5, vue)
        self.T.objects.create(title="아직 안 쓴 글", stage="post", target="memorily")
        url = reverse("posts:published")
        res = self.client.get(url)
        self.assertEqual(res.context["ACTIVE_MENU"], "posts_published")
        # 사이트(운영 순서: memorily → 눈잎) → 카테고리 순서(뷰 → 자바) → 발행일 최근이 위
        self.assertEqual([p.title for p in res.context["posts"]], ["뷰 글", "자바 새글", "자바 옛글", "눈잎 글"])
        self.assertContains(res, "memorily › 자바")  # 묶음 머리
        res = self.client.get(url, {"today": "1"})
        self.assertEqual([p.title for p in res.context["posts"]], ["눈잎 글"])  # 오늘 발행한 글
        res = self.client.get(url, {"site": "memorily", "q": "자바"})
        self.assertEqual([p.title for p in res.context["posts"]], ["자바 새글", "자바 옛글"])
        self.assertNotContains(res, "custom=1")  # 조건은 검색 · 오늘 · 사이트 · 전체만
        self.assertContains(res, ">전체</a>", html=False)

    def test_refresh_marks_placement_published(self):
        """갱신 = 모니터링 '발행 확인': 사이트에 올라온 글과 제목이 같으면 넣은 곳·글이 발행 완료 → 게시글 관리로"""
        from django.utils import timezone

        from apps.blog_ops import feeds
        blog = Blog.objects.get(name="memorily")
        cat = SiteCategory.objects.create(blog=blog, name="자바")
        post = self.T.objects.create(title="자바 스트림 정리", stage="post", target="memorily")
        pl = Placement.objects.create(site_category=cat, tistory_post=post)
        feeds.record(blog, True, "", [("자바 스트림 정리", "https://jinbaam.tistory.com/9", timezone.now())], where="PC")
        pl.refresh_from_db(), post.refresh_from_db()
        self.assertEqual((pl.status, post.publish_status), ("published", "done"))
        self.assertEqual([p.title for p in self.client.get(reverse("posts:published")).context["posts"]], ["자바 스트림 정리"])

    def test_site_links_bar(self):
        from .models import SiteLink
        seeded = list(SiteLink.objects.values_list("url", flat=True))
        self.assertIn("https://blog.naver.com/black_lukey", seeded)  # 처음 값은 운영 사이트 주소
        res = self.client.get(reverse("posts:planned"))
        self.assertContains(res, 'class="site-links"')
        self.assertContains(res, 'href="https://blog.naver.com/black_lukey" target="_blank"')
        self.assertNotContains(self.client.get(reverse("memos:list")), 'class="site-links"')  # 블로그·카페 밖에서는 없다
        back = reverse("posts:planned")
        self.client.post(reverse("blog_types:link_add"), {"name": "눈잎 글쓰기", "url": "nunip.tistory.com/manage/newpost", "next": back})
        link = SiteLink.objects.get(name="눈잎 글쓰기")
        self.assertEqual(link.url, "https://nunip.tistory.com/manage/newpost")
        self.assertEqual(link, list(SiteLink.objects.all())[-1])
        self.client.post(reverse("blog_types:link_move", args=[link.pk]), {"dir": "up", "next": back})
        self.assertEqual(list(SiteLink.objects.all())[-2], link)
        self.client.post(reverse("blog_types:link_save", args=[link.pk]), {"name": "글쓰기", "url": "javascript:alert(1)", "next": back})
        link.refresh_from_db()
        self.assertEqual(link.name, "눈잎 글쓰기")  # 틀린 주소면 그대로
        res = self.client.post(reverse("blog_types:link_save", args=[link.pk]), {"name": "글쓰기", "url": "https://a.tistory.com/manage", "next": back})
        self.assertRedirects(res, back, fetch_redirect_response=False)
        link.refresh_from_db()
        self.assertEqual((link.name, link.url), ("글쓰기", "https://a.tistory.com/manage"))
        self.client.post(reverse("blog_types:link_delete", args=[link.pk]), {"next": back})
        self.assertFalse(SiteLink.objects.filter(pk=link.pk).exists())


class DefaultPlacementTests(TestCase):
    """발행예정글로 옮기면 원고의 '넣을 카테고리'(처음 겨냥한 사이트 › 카테고리)에 넣는다 (2026-10-23 사용자)"""

    DRAFT = ("# [원고] T200 · 시험\n\n사이트: black_lukey\n\n| 항목 | 내용 |\n|---|---|\n| 넣을 카테고리 | black_lukey › 지역놀거리 (신설) |\n\n"
             "<!-- 본문 시작 -->\n# 공주 당일치기\n본문\n<!-- 본문 끝 -->\n")

    def setUp(self):
        import tempfile
        from pathlib import Path
        self.client.force_login(get_user_model().objects.create_user("tester", password="pw-test-1234"))
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        folder = Path(tmp.name) / "T200_시험"
        folder.mkdir()
        (folder / "원고.md").write_text(self.DRAFT, encoding="utf-8")
        paths = override_settings(WRITING_DRAFTS_DIR=Path(tmp.name), REPO_ROOT=Path(tmp.name))
        paths.enable()
        self.addCleanup(paths.disable)
        blog = Blog.objects.get(name="black_lukey")
        self.cat = SiteCategory.objects.create(blog=blog, name="지역 놀거리 ", order=90)

    def test_move_to_post_places_draft_category(self):
        from apps.writing.drafts import list_drafts
        from apps.writing.models import Post
        self.assertEqual(list_drafts()[0].place, "black_lukey › 지역놀거리")
        post = Post.objects.create(title="공주 당일치기", stage="review")
        self.client.post(reverse("writing:move"), {"pk": post.pk, "to": "post"})
        self.assertEqual([pl.site_category for pl in post.placements.all()], [self.cat])
        # 사용자가 뺀(휴지통) 뒤에는 목록을 열어도 다시 넣지 않는다
        post.placements.first().delete()
        self.client.get(reverse("posts:planned"))
        self.assertFalse(post.placements.exists())

    def test_planned_list_fills_never_placed(self):
        from apps.writing.models import Post
        post = Post.objects.create(title="공주 당일치기", stage="post")
        other = Post.objects.create(title="원고 없는 글", stage="post")
        self.client.get(reverse("posts:planned"))
        self.assertEqual(post.placements.count(), 1)
        self.assertEqual(other.placements.count(), 0)

    def test_monitoring_converts_without_picking(self):
        """모니터링 (2026-10-23 사용자): '발행예정으로' 옮긴 글·오늘 예정 글은 원고의 넣을 카테고리로 — 고르는 화면 없이 '변환',
        그 칸에 '전체 변환'."""
        from django.utils import timezone

        from apps.writing.models import Post
        temp = Post.objects.create(title="공주 당일치기", stage="temp", target="black_lukey")
        self.client.post(reverse("posts:promote"), {"ids": f"tistory:{temp.pk}", "next": "/blog/ops/"})
        self.assertEqual([pl.site_category for pl in temp.placements.all()], [self.cat])
        temp.placements.all().delete()  # 휴지통 — 다시 넣지 않는다
        other = Post.objects.create(title="공주 당일치기", stage="post", target="black_lukey", planned_on=timezone.localdate())
        res = self.client.get(reverse("blog_ops:index"))
        pl = other.placements.get()
        self.assertEqual(pl.site_category, self.cat)
        self.assertFalse(temp.placements.exists())
        self.assertEqual(res.context["ready_ids"], [pl.pk])
        self.assertContains(res, f'data-st-run="{pl.pk}" data-st-count="1"', html=False)  # 전체 변환
        self.assertContains(res, f'data-st-run="{pl.pk}" data-st-url=', html=False)  # 줄마다 변환 (카테고리 고르기 아님)

    def test_ai_news_goes_to_memorily_ai(self):
        """AI 소식은 원고의 넣을 카테고리(예: memorily › 기타)보다 memorily › AI 가 먼저 (2026-10-23 사용자: 발행 때 매핑)"""
        from django.conf import settings as dj_settings

        from apps.writing.models import Post
        folder = dj_settings.WRITING_DRAFTS_DIR / "T201_AI소식"
        folder.mkdir()
        (folder / "원고.md").write_text(
            "# [원고] T201 · 오늘의 AI 소식\n사이트: memorily\n고정주제: AI 소식\n\n| 항목 | 내용 |\n|---|---|\n"
            "| 넣을 카테고리 | memorily › 기타 |\n\n<!-- 본문 시작 -->\n# 오늘의 AI 소식\n본문\n<!-- 본문 끝 -->\n", encoding="utf-8")
        post = Post.objects.create(title="오늘의 AI 소식", stage="post", target="memorily")
        self.client.get(reverse("posts:planned"))
        self.assertEqual([str(pl.site_category) for pl in post.placements.all()], ["IT·AI (컨셉: AI 소식)"])  # 2026-10-31 갈래
        ai = SiteCategory.objects.get(blog__name="memorily", name="AI 소식")
        self.assertTrue(ai.heading_bar)
        # memorily 글 분류: AI + 총정리 3개 (0052) — AI 는 하나뿐
        # AI → IT·AI, 총정리 셋은 그 아래 고정 주제로, 애니 소재 (routines 0023, 2026-10-31 사용자)
        self.assertEqual(list(Category.objects.filter(section__name="memorily").values_list("name", flat=True)), ["IT·AI", "애니"])


class MemorilyAiPickTests(TestCase):
    """글 분류의 memorily › AI 는 일일 분량(기본 소재)에 들지 않는다 — memorily 는 글쓰기 루틴을 끈 사이트 (2026-10-23)"""

    def test_default_picks_skip_routine_off_site(self):
        from datetime import date

        from apps.routines.models import FixedTopic
        from apps.routines.views import default_picks
        ai = Category.objects.get(section__name="memorily", name="IT·AI")  # 옛 AI (routines 0023)
        picks = default_picks(date(2026, 10, 23))
        self.assertNotIn(ai.sel, picks)
        self.assertIn(Category.objects.get(section__name="밤밤", name="코스피 시황 노트").sel, picks)
        self.assertEqual(FixedTopic.objects.get(name="AI 소식").category, ai)  # 고정 주제의 소재 → 원고 '분류: memorily > IT·AI'


class NunipJapanConceptTests(TestCase):
    """눈잎 › 일본 여행 컨셉 (2026-10-23 사용자) · 교토 단풍 글을 새 원고로 바꾸기."""

    def test_concept_and_rewrite(self):
        from importlib import import_module

        from django.apps import apps as django_apps

        from apps.writing.models import Post
        cat = SiteCategory.objects.get(blog__name="눈잎", name="일본 여행")
        self.assertIn("권역", cat.concept)
        self.assertIn("공항에서 도심", cat.concept)
        mig = import_module("apps.writing.migrations.0022_rewrite_t112")
        post = Post.objects.create(title=mig.OLD_TITLE, body="옛 본문", stage="temp", target="눈잎")
        pl = Placement.objects.create(site_category=cat, tistory_post=post, convert_status="done")
        mig.forward(django_apps, None)
        post.refresh_from_db(), pl.refresh_from_db()
        self.assertIn("오사카 3박 4일", post.title)
        self.assertIn("## 한눈에 보는 일정", post.body)
        self.assertEqual(pl.convert_status, "none")


class SitesOverhaulTests(TestCase):
    """0028 (2026-10-26 사용자): 제품소개 빼기 · 밤밤 시황 노트."""

    def test_migrated_classes_and_concepts(self):
        bam = list(Category.objects.filter(section__name="밤밤").values_list("name", flat=True))
        self.assertIn("코스피 시황 노트", bam)  # 0028 의 시황 노트는 0033 에서 다시 나뉨
        for gone in ("상품 추천", "그 외", "코스피", "나스닥", "시황 노트"):
            self.assertNotIn(gone, bam)
        self.assertNotIn("상품 추천", Blog.objects.get(name="밤밤").content)
        daily = SiteCategory.objects.get(blog__name="눈잎", name="일상", parent=None)
        self.assertTrue(daily.concept.startswith("사용자가 직접 쓰는 일상 글" + chr(10) * 2 + "화면 모양"))  # 제품 소개 짜임은 빠지고 화면 모양만
        self.assertNotIn("제품", daily.concept)

    def test_product_posts_and_placements_go_to_trash(self):
        from importlib import import_module

        from django.apps import apps as django_apps

        from apps.core.models import TrashEntry
        from apps.writing.models import Post
        bam = Section.objects.get(name="밤밤")
        Category.objects.create(section=bam, code="X", name="시황 노트")  # 0033 이전 상태
        product = Category.objects.create(section=bam, code="Z", name="상품 추천")
        stock = Category.objects.create(section=bam, code="Y", name="나스닥")
        post = Post.objects.create(title="스탠리 퀜처 사도 될까", bt_category=product)
        pl = Placement.objects.create(site_category=SiteCategory.objects.filter(blog__name="눈잎").first(), tistory_post=post)
        night = Post.objects.create(title="나스닥 마감", bt_category=stock)
        keep = Post.objects.create(title="다른 글", bt_category=Category.objects.get(section__name="눈잎", name="일본"))
        import_module("apps.blog_types.migrations.0028_sites_overhaul").forward(django_apps, None)
        self.assertFalse(Post.objects.filter(pk=post.pk).exists())
        self.assertFalse(Placement.objects.filter(pk=pl.pk).exists())
        entry = TrashEntry.objects.get(model_label="writing.post", object_key=str(post.pk))
        self.assertEqual(entry.members["blog_types.placement"], [pl.pk])
        self.assertFalse(Category.objects.filter(pk__in=[product.pk, stock.pk]).exists())
        night.refresh_from_db()
        self.assertEqual(night.bt_category.name, "시황 노트")  # 나스닥 글은 시황 노트로
        self.assertTrue(Post.objects.filter(pk=keep.pk).exists())


class MarketNotesSplitTests(TestCase):
    """0033 (2026-10-26 사용자: 코스피를 다음 날 아침에 보는 건 늦다): 시황 노트 → 코스피 · 나스닥 두 시리즈."""

    def test_split_after_migrate(self):
        bam = list(Category.objects.filter(section__name="밤밤").values_list("name", flat=True))
        self.assertEqual(bam[:2], ["코스피 시황 노트", "나스닥 시황 노트"])
        self.assertTrue(Blog.objects.get(name="밤밤").content.startswith("코스피 시황 노트"))

    def test_restores_trashed_nasdaq_and_moves_its_posts(self):
        from datetime import timedelta
        from importlib import import_module

        from django.apps import apps as django_apps
        from django.utils import timezone

        from apps.core.models import TrashEntry
        from apps.writing.models import Post
        bam = Section.objects.get(name="밤밤")
        Category.all_objects.filter(section=bam, name__endswith="시황 노트").delete()
        market = Category.objects.create(section=bam, code="A", name="시황 노트", order=1)  # 0028 뒤 상태
        when = timezone.now() - timedelta(days=1)
        nasdaq = Category.objects.create(section=bam, code="B", name="나스닥", order=2)
        Category.all_objects.filter(pk=nasdaq.pk).update(deleted_at=when)
        TrashEntry.objects.create(model_label="blog_types.category", object_key=str(nasdaq.pk), title="밤밤 › 나스닥",
                                  section="카테고리 관리 · 카테고리", deleted_at=when, members={"blog_types.category": [nasdaq.pk]})
        night = Post.objects.create(title="나스닥 2.6% 급락", bt_category=market)
        both = Post.objects.create(title="코스피 반등, 간밤 나스닥은", bt_category=market)
        import_module("apps.blog_types.migrations.0033_market_notes_split").forward(django_apps, None)
        self.assertEqual(Category.objects.get(pk=market.pk).name, "코스피 시황 노트")
        self.assertEqual(Category.objects.get(pk=nasdaq.pk).name, "나스닥 시황 노트")  # 휴지통에서 되살림
        self.assertFalse(TrashEntry.objects.filter(object_key=str(nasdaq.pk), model_label="blog_types.category").exists())
        night.refresh_from_db(), both.refresh_from_db()
        self.assertEqual(night.bt_category_id, nasdaq.pk)
        self.assertEqual(both.bt_category_id, market.pk)  # 코스피 글은 그대로
        stock = SiteCategory.objects.filter(blog__name="밤밤", name="주식").first()
        if stock:
            self.assertIn("시황 노트 두 시리즈", stock.concept)


class PlacementChangedTests(TestCase):
    """게시글 관리 '수정됨' 불 (2026-10-26 사용자): 발행 뒤 바뀌면 켜지고, 누르거나 RSS 에 새 제목이 보이면 꺼진다."""

    def setUp(self):
        from apps.core.models import ROUTINE_BRIEF_TOKEN_KEY, AppSetting
        from apps.writing.models import Post
        AppSetting.set(ROUTINE_BRIEF_TOKEN_KEY, "tok")
        self.client.force_login(get_user_model().objects.create_user("tester", password="pw-test-1234"))
        self.cat = SiteCategory.objects.filter(blog__name="눈잎").first()
        self.post = Post.objects.create(title="옛 제목", body="본문", stage="post", publish_status="done", target="눈잎")
        self.pl = Placement.objects.create(site_category=self.cat, tistory_post=self.post, status=Placement.Status.PUBLISHED,
                                           converted_title="옛 제목", converted_body="옛 본문", convert_status=Placement.Convert.DONE)

    def save(self, **data):
        return self.client.post(reverse("site_templates:api_save", args=[self.pl.pk]) + "?token=tok", data)

    def test_resend_converted_body_lights_lamp_and_seen_clears_it(self):
        self.save(body="옛 본문")
        self.pl.refresh_from_db()
        self.assertIsNone(self.pl.changed_at)  # 같은 본문이면 그대로
        self.save(title="새 제목", body="새 본문")
        self.pl.refresh_from_db()
        self.assertIsNotNone(self.pl.changed_at)
        self.assertEqual(self.pl.changed_note, "제목·본문 · 옛 제목 → 새 제목")
        res = self.client.get(reverse("posts:published"))
        self.assertContains(res, 'class="pl-lamp on"')
        self.assertContains(res, "수정됨 <span class=\"cnt\">1</span>")
        self.assertContains(self.client.get(reverse("posts:published"), {"changed": "1"}), "옛 제목")
        self.client.post(reverse("blog_types:place_seen", args=[self.pl.pk]))
        self.pl.refresh_from_db()
        self.assertIsNone(self.pl.changed_at)
        self.assertNotContains(self.client.get(reverse("posts:published")), 'class="pl-lamp on"')

    def test_unpublished_placement_does_not_light(self):
        Placement.objects.filter(pk=self.pl.pk).update(status=Placement.Status.UNSAVED)
        self.save(body="새 본문")
        self.pl.refresh_from_db()
        self.assertIsNone(self.pl.changed_at)

    def test_feed_with_new_title_clears_lamp(self):
        from datetime import datetime, timezone as dt_tz

        from apps.blog_ops.feeds import clear_changed
        self.save(title="새 제목", body="새 본문")
        blog = self.cat.blog
        self.assertEqual(clear_changed(blog, [("옛 제목", "u", datetime.now(dt_tz.utc))]), 0)
        self.assertEqual(clear_changed(blog, [("새 제목", "u", datetime.now(dt_tz.utc))]), 1)
        self.pl.refresh_from_db()
        self.assertIsNone(self.pl.changed_at)


class WordpressSitesTests(TestCase):
    """0030 (2026-10-26 사용자): 워드프레스 jinbaam.com 을 글쓰기 루틴에 — 소재·사이트 카테고리 넷. 눈잎의 동물은 걷어 낸다."""
    NAMES = ["산과 캠핑", "드라이브·자동차", "국내여행", "해외여행"]

    def test_wordpress_classes_categories_and_template(self):
        from apps.site_templates.models import PlatformFormat, SiteTemplate
        wp = Blog.objects.get(platform="wordpress")
        self.assertEqual((wp.status, wp.routine, wp.address), ("active", True, "https://jinbaam.com/"))
        self.assertEqual(list(Category.objects.filter(section__name=wp.name).values_list("name", flat=True)), self.NAMES)
        cats = SiteCategory.objects.filter(blog=wp, parent=None).order_by("order")
        self.assertEqual(list(cats.values_list("name", flat=True)), ["산과 캠핑", "드라이브·자동차", "Korea Travel", "World Travel"])
        self.assertIn("日本語まとめ", cats.get(name="Korea Travel").concept)
        self.assertIn("자동차", SiteTemplate.objects.get(blog=wp).tone + cats.get(name="드라이브·자동차").concept)
        self.assertNotIn("사진은 넣지 않는다", PlatformFormat.objects.get(platform="wordpress").guide)
        self.assertTrue(wp.checks.filter(body__startswith="국내여행·해외여행은 영어 본문").exists())

    def test_no_animal_left_on_nunip(self):
        from apps.site_templates.models import SiteTemplate
        self.assertFalse(Category.objects.filter(section__name="눈잎", name="동물").exists())
        self.assertFalse(SiteCategory.objects.filter(blog__name="눈잎", name="동물").exists())
        self.assertNotIn("동물", Blog.objects.get(name="눈잎").content)
        self.assertNotIn("동물", SiteTemplate.objects.get(blog__name="눈잎").tone)
        for launch in SiteCategory.objects.filter(blog__name="black_lukey", name="출시"):  # 자동차 출시는 워드프레스
            self.assertNotIn("자동차", launch.concept)

    def test_animal_posts_go_to_trash(self):
        from importlib import import_module

        from django.apps import apps as django_apps

        from apps.writing.models import Post
        nunip = Section.objects.get(name="눈잎")
        animal = Category.objects.create(section=nunip, code="Z", name="동물")
        post = Post.objects.create(title="금붕어 기억력", bt_category=animal)
        import_module("apps.blog_types.migrations.0030_wordpress_sites").forward(django_apps, None)
        self.assertFalse(Post.objects.filter(pk=post.pk).exists())
        self.assertFalse(Category.objects.filter(pk=animal.pk).exists())


class WordpressLooksTests(TestCase):
    """0032 (2026-10-26 사용자): 워드프레스 카테고리 글 모양·컨셉, 붙여넣기 포맷, 바로가기."""

    def test_looks_concepts_format_links(self):
        from apps.site_templates.models import PlatformFormat
        from .models import SiteLink
        cats = {c.name: c for c in SiteCategory.objects.filter(blog__platform="wordpress", parent=None)}
        self.assertEqual({n: c.look for n, c in cats.items()},
                         {"산과 캠핑": "wp_mountain", "드라이브·자동차": "wp_car", "Korea Travel": "wp_travel", "World Travel": "wp_travel"})
        self.assertIn("기관별 절정일 비교", cats["산과 캠핑"].concept)
        self.assertIn("C. 기능·노하우", cats["드라이브·자동차"].concept)
        # 0036 (2026-10-27 사용자): 차 소재는 신차·제도 말고도 무궁무진 — 상시 소재 E~H
        self.assertIn("E. 차 종류·구조 해설", cats["드라이브·자동차"].concept)
        self.assertLess(cats["드라이브·자동차"].concept.index("H. 상식·통계"), cats["드라이브·자동차"].concept.index("- 숫자는 제조사"))
        self.assertIn("차 한 대 깊게", Category.objects.get(section__name="워드프레스", name="드라이브·자동차").direction)
        self.assertIn("## 日本語まとめ", cats["Korea Travel"].concept)
        self.assertIn("Entry & Money Checklist", cats["World Travel"].concept)
        self.assertIn("코드 편집기", PlatformFormat.objects.get(platform="wordpress").guide)
        self.assertTrue(SiteLink.objects.filter(url="https://jinbaam.com/wp-admin/post-new.php").exists())


class ChangeNoteTests(TestCase):
    """'수정됨' 한 줄 (2026-10-26 사용자): 제목만 / 본문만 / 제목·본문 + 무엇을, 변환글 보기 맨 위."""

    def test_note_shapes_and_old_title(self):
        from .sites import change_note, changed_old_title
        self.assertEqual(change_note("가", "나", False), "제목만 · 가 → 나")
        self.assertEqual(change_note("가", "가", True, "맨 앞 한 문장 추가"), "본문만 · 맨 앞 한 문장 추가")
        self.assertEqual(changed_old_title(change_note("가", "나", True)), "가")
        self.assertEqual(changed_old_title("제목: 옛 → 새"), "옛")
        self.assertIsNone(changed_old_title("본문만"))

    def test_panel_shows_note_only_when_changed(self):
        from apps.core.models import ROUTINE_BRIEF_TOKEN_KEY, AppSetting
        from apps.writing.models import Post
        AppSetting.set(ROUTINE_BRIEF_TOKEN_KEY, "tok")
        self.client.force_login(get_user_model().objects.create_user("tester", password="pw-test-1234"))
        post = Post.objects.create(title="옛 제목", body="본문", stage="post", publish_status="done")
        pl = Placement.objects.create(site_category=SiteCategory.objects.filter(blog__name="눈잎").first(), tistory_post=post,
                                      status=Placement.Status.PUBLISHED, converted_title="옛 제목", converted_body="옛 본문",
                                      convert_status=Placement.Convert.DONE)
        page = reverse("site_templates:post") + f"?p=tistory:{post.pk}"
        self.assertNotContains(self.client.get(page), 'class="cv-changed"')
        self.client.post(reverse("site_templates:api_save", args=[pl.pk]) + "?token=tok",
                         {"title": "옛 제목", "body": "한 문장\n\n옛 본문", "change": "맨 앞 한 문장 추가"})
        res = self.client.get(page)
        self.assertContains(res, 'class="cv-changed"')
        self.assertContains(res, "본문만 · 맨 앞 한 문장 추가")


class FixDashTitlesMigrationTests(TestCase):
    """0034 (2026-10-26): curl 명령줄(cp949)에서 ? 로 깨진 변환본 제목의 줄표를 되살린다. 진짜 물음표는 그대로."""

    def test_forward(self):
        from importlib import import_module
        from django.apps import apps as django_apps
        from apps.writing.models import Post
        cat = SiteCategory.objects.filter(blog__platform="wordpress").first()
        broken = Placement.objects.create(site_category=cat, tistory_post=Post.objects.create(title="민둥산 억새 — 증산초", stage="post", body="b"),
                                          converted_title="민둥산 억새 등산코스 ? 증산초 완만")
        question = Placement.objects.create(site_category=cat, tistory_post=Post.objects.create(title="몇 화부터? 환산기", stage="post", body="b"),
                                            converted_title="블리치 몇 화부터 ? 환산기")
        import_module("apps.blog_types.migrations.0034_fix_dash_titles").forward(django_apps, None)
        broken.refresh_from_db()
        question.refresh_from_db()
        self.assertEqual(broken.converted_title, "민둥산 억새 등산코스 — 증산초 완만")
        self.assertEqual(question.converted_title, "블리치 몇 화부터 ? 환산기")  # 원문에 — 가 없으면 손대지 않는다


class TravelPhotosMaxMigrationTests(TestCase):
    """0050 (2026-10-29 사용자): 여행 카테고리 사진 장수는 바닥이 아니라 상한."""

    def test_forward(self):
        from importlib import import_module
        from django.apps import apps as django_apps
        cat = SiteCategory.objects.filter(blog__name="워드프레스", name="World Travel").first()
        cat.concept = "사진은 그 장소가 실제로 찍힌 무료 사진 — 맨 위 대표 1장 + Day 마다 그날 주인공 장소 1~2장, 글 전체 4장 이상 (2026-10-27 사용자: 로마편 사진이 없다). 끝"
        cat.save()
        import_module("apps.blog_types.migrations.0050_travel_photos_max").forward(django_apps, None)
        cat.refresh_from_db()
        self.assertIn("괜찮은 것만, 글 전체 많아야 9장", cat.concept)
        self.assertNotIn("4장 이상", cat.concept)


class LocalLunchCafeTests(TestCase):
    """blog_types 0051 (2026-10-29 사용자): black_lukey › 지역 놀거리 점심·카페를 동선 중간에, 합쳐 최대 3곳, 괜찮으면 넣는다."""

    def test_concept_lines(self):
        from importlib import import_module

        from django.apps import apps as django_apps
        mig = import_module("apps.blog_types.migrations.0051_local_lunch_cafe")
        blog = Blog.objects.get(name="black_lukey")
        SiteCategory.objects.filter(blog=blog, name="지역 놀거리").delete()
        cat = SiteCategory.objects.create(blog=blog, name="지역 놀거리",
                                          concept="- 순서: 인용 → 하루 시간표 " + mig.OLD_ORDER + "\n" + mig.OLD_FOOD + "\n- 끝")
        fest = SiteCategory.objects.filter(blog=blog).exclude(pk=cat.pk).first() or SiteCategory.objects.create(blog=blog, name="축제·행사")
        fest.concept = mig.OLD_FOOD
        fest.save()
        mig.forward(django_apps, None)
        mig.forward(django_apps, None)  # 두 번 돌아도 그대로
        cat.refresh_from_db(), fest.refresh_from_db()
        self.assertEqual(cat.concept, "- 순서: 인용 → 하루 시간표 " + mig.NEW_ORDER + "\n" + mig.NEW_FOOD + "\n- 끝")
        self.assertIn("합쳐 최대 3곳", cat.concept)
        self.assertEqual(fest.concept, mig.OLD_FOOD)  # 축제·행사는 그대로
