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
    Section.all_objects.filter(name__in=["눈잎", "black_lukey", "밤밤"]).delete()
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
        self.assertEqual(names, ["Vue.js, Node.js", "Java", "Database", "Android Studio", "Make",
                                 "공모전 및 프로젝트", "자격증", "일상생활", "기타"])
        self.assertEqual(SiteCategory.objects.filter(blog__name="black_lukey").count(), 2)
        self.assertEqual(SiteCategory.objects.filter(blog__name="눈잎").count(), 6)  # 0019 티스토리 화면 그대로

    def test_tree_shows_both_grids(self):
        res = self.client.get(INDEX)
        self.assertContains(res, "글 분류")
        self.assertContains(res, "사이트 카테고리")
        self.assertContains(res, "Android Studio")
        self.assertContains(res, "카테고리 없음")  # 눈잎·밤밤
        res = self.client.get(INDEX, {"sel": self.memorily.sel})
        self.assertContains(res, "https://jinbaam.tistory.com/")
        self.assertNotContains(res, "자세한 내용 · 고치기")  # 사이트 자체는 규칙 화면에서 고친다

    def test_add_edit_move_delete(self):
        self.add(self.memorily.sel, "AI 이야기")
        top = SiteCategory.objects.get(name="AI 이야기")
        self.assertEqual((top.blog, top.parent, top.order), (self.memorily, None, 10))
        self.add(top.sel, "Claude Code")
        sub = SiteCategory.objects.get(name="Claude Code")
        self.assertEqual(sub.parent, top)
        res = self.add(sub.sel, "3단")  # 하위 카테고리 아래로는 못 만든다
        self.assertFalse(SiteCategory.objects.filter(name="3단").exists())
        self.client.post(reverse("blog_types:save", args=["sitecat", top.pk]), {"name": "AI 개발기", "note": "새 축"})
        top.refresh_from_db()
        self.assertEqual((top.name, top.note), ("AI 개발기", "새 축"))
        self.client.post(reverse("blog_types:move", args=["sitecat", top.pk]), {"dir": "up"})
        self.assertEqual(SiteCategory.objects.filter(blog=self.memorily, parent=None)[8].name, "AI 개발기")
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
        java = SiteCategory.objects.get(blog=memorily, name="Java")
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
        java = SiteCategory.objects.get(blog__name="memorily", name="Java")
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
        res = self.client.get(reverse("video:list"))
        self.assertContains(res, "영상 콘텐츠 리스트")  # 블로그·카페 리스트는 뺐다 (listing=False)
        self.assertNotContains(res, "블로그·카페 리스트")
        self.assertContains(res, 'class="nav-item nav-toggle" data-nav-toggle')
        group = next(n for n in res.context["NAV"] if n["menu"].key == "video")
        self.assertTrue(group["open"])
        self.assertTrue(group["children"][0]["active"])  # 리스트 중메뉴가 강조된다
        memos = next(n for n in res.context["NAV"] if n["menu"].key == "memos")
        self.assertEqual(memos["children"], [])  # 하위 없는 메뉴는 그대로


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

        res = self.client.get(view, {"stage": "review"})  # 고른 글이 없으면 그 단계의 첫 글
        self.assertEqual(res.context["post"].title, "검토 중인 글")
        self.assertEqual([p.title for p in res.context["pl_items"]], ["검토 중인 글"])
        self.T.objects.filter(stage="review").delete()
        res = self.client.get(view, {"stage": "review"})  # 글이 없는 단계
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
        """임시글·검토글 (2026-10-22 사용자): 기본은 한 건씩, '목록'으로 바꾸면 체크해서 한꺼번에 옮기기·삭제"""
        a = self.T.objects.create(title="임시 하나", stage="temp")
        b = self.N.objects.create(title="임시 둘", stage="temp")
        view = reverse("posts:view")
        res = self.client.get(view, {"stage": "temp"})  # 기본: 한 건씩 (글 화면) + 보기 바꾸기
        self.assertIn("post", res.context)
        self.assertContains(res, f'href="{view}?stage=temp&amp;view=list"')
        res = self.client.get(view, {"stage": "temp", "view": "list"})
        self.assertEqual(sorted(p.title for p in res.context["posts"]), ["임시 둘", "임시 하나"])
        self.assertContains(res, f'value="tistory:{a.pk}" form="ph-bulk"')
        self.assertContains(res, f'href="{view}?stage=temp&amp;p=tistory:{a.pk}"')  # 제목은 한 건씩 보기로
        self.assertContains(res, f'href="{view}?stage=review&amp;view=list"')  # 다른 단계 탭도 목록으로
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
        nav = [c.title for m in res.context["MENUS"] if m.key == "blog" for c in m.children]
        self.assertEqual(nav[:3], ["글 관리", "카테고리 관리", "사이트별 템플릿"])
        self.assertNotIn("운영", nav)
        self.assertEqual(nav[-2:], ["모니터링", "논의 현황"])

    def test_today_filter(self):
        from datetime import timedelta

        from django.utils import timezone

        self.T.objects.create(title="오늘 글", stage="temp")
        old = self.N.objects.create(title="어제 글", stage="temp")
        self.N.objects.filter(pk=old.pk).update(created_at=timezone.now() - timedelta(days=1))
        res = self.client.get(reverse("posts:view"), {"stage": "temp", "today": "1"})
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
        res = self.client.get(reverse("posts:view"), {"stage": "temp", "custom": "1"})
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
        res = self.client.get(url)
        self.assertEqual(sorted(p.title for p in res.context["pl_items"]), ["네 임시", "티 임시"])
        self.assertEqual([t["count"] for t in res.context["pl_tabs"]], [2, 1, 0, 0])  # … 발행예정글 · 게시글 관리
        res = self.client.get(url, {"sel": "u", "stage": "review"})
        self.assertEqual([p.title for p in res.context["pl_items"]], ["티 검토"])  # 미분류
        res = self.client.get(url, {"sel": self.season.category.sel})
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
        tree = self.client.get(INDEX).context["tree"]
        self.assertEqual(tree["unclassified"], 1)
        res = self.client.get(INDEX, {"sel": "u"})
        self.assertEqual([x.title for x in res.context["posts"]], ["분류 없는 포스트"])
        java = SiteCategory.objects.get(blog__name="memorily", name="Java")
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
        self.assertContains(res, f'{reverse("posts:view")}?stage=review"')  # 단계 탭은 글 관리 안에서


class MappingPanesTests(TestCase):
    """카테고리 관리 오른쪽: 위 매핑 · 아래 글을 함께, 트리를 누르면 그 칸만"""

    def setUp(self):
        legacy_tree()
        user = get_user_model().objects.create_user("tester", password="pw-test-1234")
        self.client.force_login(user)
        from apps.writing.models import Post
        self.java = SiteCategory.objects.get(blog__name="memorily", name="Java")
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
        self.java = SiteCategory.objects.get(blog__name="memorily", name="Java")
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
        # 게시글 관리 (2026-10-22 사용자): 발행예정글 다음 탭, 발행 완료한 글
        res = self.client.get(url, {"stage": "done"})
        self.assertEqual([p.title for p in res.context["posts"]], ["발행한 글"])
        self.assertEqual([(t["label"], t["count"]) for t in res.context["tabs"]][2:], [("발행예정글", 3), ("게시글 관리", 1)])
        self.assertContains(res, "wr-compact")  # 발행예정글과 같은 표
        view = self.client.get(url, {"p": f"tistory:{done.pk}"})
        self.assertEqual(view.context["pl_stage"], "done")  # 글 보기 왼쪽 목록도 게시글 관리
        self.T.objects.create(title="임시", stage="temp")
        res = self.client.get(url, {"stage": "temp"})
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
        self.assertContains(res, 'id="rc-note"')  # 재변환 코멘트 칸
        self.assertContains(res, 'data-reconvert data-url="/blog/site-templates/reconvert/"')
        self.assertContains(res, f'data-st-run="{self.pl.pk}"')  # 줄의 변환 버튼
        page = self.client.get(reverse("site_templates:post"), {"p": f"tistory:{self.a.pk}", "back": "/blog/posts/view/?stage=post"})
        self.assertEqual(page.context["ACTIVE_MENU"], "posts_view")
        self.assertContains(page, "아직 변환본이 없습니다")
        self.assertContains(page, 'href="/blog/posts/view/?stage=post"')  # 글 관리로 돌아가기
        nocat = self.client.get(reverse("site_templates:post"), {"p": f"naver:{self.b.pk}"})
        self.assertContains(nocat, "카테고리 고르기")  # 넣은 곳이 없으면 여기서 바로 넣는다
        self.assertEqual((res.context["ready_ids"], res.context["ready_count"]), (str(self.pl.pk), 1))  # 전체 변환
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
        self.assertEqual(list(Section.objects.values_list("name", flat=True)), ["눈잎", "black_lukey", "밤밤"])
        self.assertEqual(list(Category.objects.filter(section__name="밤밤").values_list("name", flat=True)),
                         ["코스피", "나스닥", "상품 추천", "그 외"])
        self.assertTrue(all(s.categories.filter(name="그 외").exists() for s in Section.objects.all()))  # 사이트마다 '그 외' 하나
        self.assertFalse(PostType.objects.exists())  # 소분류 없이 소재만
        self.assertTrue(Category.objects.get(name="코스피").direction)  # 방향 = 글쓰기 컨셉
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
        self.assertContains(res, "주 1편</option>")

    def test_posts_get_new_site_and_error_post_goes_to_trash(self):
        from importlib import import_module

        from django.apps import apps as django_apps

        from apps.naver_writing.models import Post as NaverPost
        from apps.writing.models import Post
        mig = import_module("apps.blog_types.migrations.0018_site_cleanup")
        kospi = Post.objects.create(title="코스피 3.29% 반등 다음 날 다시 약세, 9거래일 종가표로 보는 지금 위치", target="눈잎")
        heat = NaverPost.objects.create(title="전기장판 vs 온수매트 vs 탄소매트, 월 전기료 직접 계산하고 고르기 (2026 겨울)", target="black_lukey")
        anime = Post.objects.create(title="나루토 회차정리 애니만화 환산기 명장면 등 모음", target="memorily",
                                    bt_category=Category.objects.get(name="그 외", section__name="눈잎"))
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
    NAMES = ["청년·신혼 정책", "주택 공고", "공모주", "해외 여행", "일본 여행", "일상"]

    def site_names(self):
        return list(SiteCategory.objects.filter(blog__name="눈잎", parent=None).order_by("order", "pk").values_list("name", flat=True))

    def test_seeded_in_tistory_order(self):
        self.assertEqual(self.site_names(), self.NAMES)
        self.assertEqual(SiteCategory.objects.get(blog__name="눈잎", name="공모주").note, "티스토리 주제: 경제")
        self.assertEqual(list(Category.objects.filter(section__name="눈잎").values_list("name", flat=True)),
                         ["청년·신혼 정책", "주택 공고", "공모주", "해외 여행", "일본 여행", "엔화·환율", "그 외"])

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
        self.assertEqual(self.site_names(), self.NAMES + ["쓰는 메뉴"])
        self.assertTrue(SiteCategory.all_objects.filter(pk=empty.pk, deleted_at__isnull=False).exists())
