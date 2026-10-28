from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse

from apps.blog_rules.models import Blog
from apps.blog_types.models import Placement, SiteCategory
from apps.writing.models import Post

from . import prompt
from .models import PlatformFormat, SiteTemplate


class SiteTemplateTests(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_user("tester", password="pw-test-1234")
        self.client.force_login(user)
        self.memorily = Blog.objects.get(name="memorily")
        self.java = SiteCategory.objects.get_or_create(blog=self.memorily, name="Java")[0]  # 옛 카테고리는 0042 에서 지웠다 — 시험용으로 만든다
        self.post = Post.objects.create(title="자바 정리", stage="post", body="## 소제목\n본문")
        self.pl = Placement.objects.create(site_category=self.java, tistory_post=self.post)

    def test_seed_and_index(self):
        """사이트별 템플릿 (2026-10-22 사용자): 변환은 글 관리로, 여기는 글쓰기·변환 컨셉과 규칙"""
        self.assertEqual(PlatformFormat.objects.count(), 4)
        self.assertIn("개발자", SiteTemplate.objects.get(blog=self.memorily).tone)
        res = self.client.get(reverse("site_templates:index"))
        self.assertContains(res, "memorily")
        self.assertContains(res, "사이트별 템플릿")  # 메뉴
        self.assertContains(res, f'href="?site={self.java.sel}"')  # 왼쪽 사이트 카테고리 트리
        self.assertNotIn("posts", res.context)  # 변환할 글 표는 없다
        self.assertNotContains(res, "변환 가능 글 전체 변환")
        self.assertContains(res, "카테고리 컨셉 0/")  # 사이트마다 요약
        res = self.client.get(reverse("site_templates:index"), {"site": self.memorily.sel})
        self.assertContains(res, "말투·멘트")  # 사이트를 고르면 컨셉·템플릿 (보기만)
        self.assertContains(res, "붙여넣기 포맷")
        self.assertContains(res, "Java")  # 카테고리 컨셉 목록
        self.assertNotContains(res, 'name="t-tone"')  # 고치는 칸 없음

    def test_category_concept(self):
        """카테고리를 고르면 그 컨셉과 같이 적용되는 것 — 보기만 (2026-10-22 사용자: 고치기는 Claude 에게 따로)"""
        self.java.concept = "자바 기초를 예제 하나로"
        self.java.save()
        url = reverse("site_templates:index")
        res = self.client.get(url, {"site": self.java.sel})
        self.assertContains(res, "자바 기초를 예제 하나로")
        self.assertContains(res, "같이 적용되는 것")
        self.assertContains(res, "개발자")  # 사이트 말투가 같이 보인다
        self.assertNotContains(res, "<textarea")  # 고치는 칸 없음
        self.assertIn("## 카테고리 컨셉\n- Java: 자바 기초를 예제 하나로", prompt.build(self.pl))  # 요청문에 카테고리 컨셉
        res = self.client.get(url, {"site": self.memorily.sel})
        self.assertNotContains(res, "<textarea")
        self.assertContains(res, "개발자")
        self.assertNotContains(res, "디자인 컨셉")  # 사이트 화면에는 없다

    def test_category_design(self):
        """카테고리 › 디자인 컨셉 (2026-10-28 사용자): 요소마다 변환과 같은 코드로 그린 견본 — 글 모양에 따라 요소가 다르다"""
        url = reverse("site_templates:index")
        res = self.client.get(url, {"site": self.java.sel})
        self.assertContains(res, "디자인 컨셉")
        keys = [it["key"] for it in res.context["design"]]
        self.assertEqual(keys, ["heading", "text", "lead", "table", "card", "photo", "hr", "source"])
        card = next(it for it in res.context["design"] if it["key"] == "card")
        self.assertIn("가 볼 곳", card["doc"])  # 티스토리 정보 카드 그대로
        photo = next(it for it in res.context["design"] if it["key"] == "photo")
        self.assertIn('src="http://testserver/static/img/design-sample-a.svg"', photo["doc"])  # 사진이 걸러지지 않는다
        self.assertContains(res, "<iframe srcdoc=")
        self.java.look = "yudi"
        self.java.save()
        card = self.client.get(url, {"site": self.java.sel}).context["design"][4]
        self.assertEqual(card["name"], "메모지 상자")
        self.assertIn("border:3px solid #bfe9e3", card["doc"])
        wp = Blog.objects.create(name="시험 워드프레스", platform=Blog.Platform.WORDPRESS)
        travel = SiteCategory.objects.create(blog=wp, name="World Travel", look="wp_travel")
        design = self.client.get(url, {"site": travel.sel}).context["design"]
        self.assertEqual([it["key"] for it in design][-2:], ["day", "lang"])
        self.assertIn('class="jb-toc"', next(it for it in design if it["key"] == "toc")["doc"])
        self.assertIn("jb-card--food", next(it for it in design if it["key"] == "card")["doc"])

    def test_reconvert_with_comment(self):
        """재변환 (2026-10-22 사용자): 글 관리에서 체크한 글 하나 + 코멘트. 변환 완료여도 다시, 지난 변환본을 코멘트대로"""
        from apps.core.models import ROUTINE_BRIEF_TOKEN_KEY, AppSetting
        AppSetting.set(ROUTINE_BRIEF_TOKEN_KEY, "tok")
        self.pl.convert_status, self.pl.converted_title, self.pl.converted_body = "done", "지난 제목", "지난 본문 첫 문단"
        self.pl.save()
        url = reverse("site_templates:reconvert")
        self.assertEqual(self.client.post(url, {"p": f"tistory:{self.post.pk}", "note": ""}).status_code, 400)
        data = self.client.post(url, {"p": f"tistory:{self.post.pk}", "note": "첫 문단을 더 짧게"}).json()
        text = data["prompt"]
        self.assertTrue(text.startswith("# 사이트 변환 (재변환)"))
        self.assertIn("## 재변환 코멘트 (사용자)\n첫 문단을 더 짧게", text)
        self.assertIn("## 지난 변환본 (재변환 코멘트대로 고친다)", text)
        self.assertIn("지난 본문 첫 문단", text)
        self.assertTrue(data["key"].startswith("rc-"))
        self.pl.refresh_from_db()
        self.assertEqual((self.pl.convert_status, self.pl.convert_note), ("requested", ""))  # 코멘트는 이번에만
        from apps.writing.models import Post as T
        lone = T.objects.create(title="안 넣은 글", stage="post")
        self.assertEqual(self.client.post(url, {"p": f"tistory:{lone.pk}", "note": "x"}).status_code, 400)

    def test_convert_brief_when_copy_fails(self):
        """2026-10-28 사용자: 전체 변환에서 '안내문을 복사하지 못했습니다' → 서버에도 두고, PC 가 링크의 key 로 한 번 받아 간다."""
        import tempfile
        from io import BytesIO
        from pathlib import Path
        from unittest.mock import patch

        from apps.core.models import ROUTINE_BRIEF_TOKEN_KEY, AppSetting
        from apps.routines.local_run import start

        AppSetting.set(ROUTINE_BRIEF_TOKEN_KEY, "tok")
        j = self.client.post(reverse("site_templates:run"), {"ids": str(self.pl.pk)}).json()
        self.assertRegex(j["key"], r"^cv-[0-9a-f]{20}$")
        self.client.logout()  # PC 실행기는 로그인 없이 받는다
        self.assertEqual(self.client.get(reverse("site_templates:brief", args=["cv-x"])).status_code, 404)
        res = self.client.get(reverse("site_templates:brief", args=[j["key"]]))
        self.assertEqual(res.content.decode("utf-8"), j["prompt"])
        self.assertEqual(self.client.get(reverse("site_templates:brief", args=[j["key"]])).status_code, 404)  # 한 번만
        link = f"jbroutine:convert?key={j['key']}&day={j['day']}"
        with tempfile.TemporaryDirectory() as tmp, override_settings(BASE_DIR=Path(tmp)), \
                patch("apps.routines.local_run.WINDOWS", True), patch("apps.routines.local_run.find_claude", return_value="claude"), \
                patch("apps.routines.local_run.open_terminal", return_value=""), \
                patch("apps.routines.local_run.urllib.request.urlopen") as urlopen:
            urlopen.return_value.__enter__.return_value = BytesIO(j["prompt"].encode("utf-8"))
            self.assertIn("사이트 변환을 시작", start(link, ""))  # 클립보드가 비었다
            self.assertIn(f"/blog/site-templates/brief/{j['key']}/", urlopen.call_args[0][0])
            self.assertTrue((Path(tmp) / ".routine" / f"{j['key']}-{j['day']}.md").read_text(encoding="utf-8").startswith("# 사이트 변환"))
            urlopen.side_effect = OSError("404")
            with self.assertRaisesRegex(ValueError, "안내문을 받지 못했습니다"):
                start(link, "")

    def test_run_needs_token_then_launches_and_api_saves(self):
        from apps.core.models import ROUTINE_BRIEF_TOKEN_KEY, AppSetting
        run = reverse("site_templates:run")
        res = self.client.post(run, {"ids": str(self.pl.pk)})
        self.assertEqual(res.status_code, 400)  # 보고 토큰이 없으면 시작하지 않는다
        self.pl.refresh_from_db()
        self.assertEqual(self.pl.convert_status, "none")
        AppSetting.set(ROUTINE_BRIEF_TOKEN_KEY, "tok-123")
        data = self.client.post(run, {"ids": f"{self.pl.pk},999"}).json()
        self.assertTrue(data["prompt"].startswith("# 사이트 변환"))
        self.assertTrue(data["key"].startswith("cv-"))
        self.assertIn("token=tok-123", data["prompt"])
        self.assertIn(f"workspace/.routine/convert/{self.pl.pk}.md", data["prompt"])
        self.assertIn("## 원문", data["prompt"])
        self.assertIn("## 사실 점검", data["prompt"])  # 변환 때 숫자·날짜·일정을 출처에서 다시 확인
        self.assertIn(f'check@workspace/.routine/convert/{self.pl.pk}-check.md', data["prompt"])
        self.assertIn("- 고침: 원래 값 → 고친 값", data["prompt"])
        self.pl.refresh_from_db()
        self.assertEqual(self.pl.convert_status, "requested")
        api = reverse("site_templates:api_save", args=[self.pl.pk])
        self.client.logout()
        self.assertEqual(self.client.post(f"{api}?token=bad", {"body": "x"}).status_code, 403)
        res = self.client.post(f"{api}?token=tok-123", {"title": "바꾼 제목", "body": "## 바꾼\r\n본문", "tags": "자바, 기초"})
        self.assertEqual(res.content.decode(), f"ok {self.pl.pk} done")
        self.pl.refresh_from_db()
        self.assertEqual((self.pl.convert_status, self.pl.converted_title, self.pl.converted_body, self.pl.converted_tags),
                         ("done", "바꾼 제목", "## 바꾼\n본문", "자바, 기초"))
        self.assertIsNotNone(self.pl.converted_at)
        # Windows curl: 명령줄의 제목·태그는 cp949, 파일로 보낸 본문은 UTF-8 (2026-10-20 제목·태그가 깨졌다)
        from urllib.parse import quote_plus
        mixed = "&".join([f"title={quote_plus('자바 제목', encoding='cp949')}", f"tags={quote_plus('자바, 기초', encoding='cp949')}",
                          f"body={quote_plus('## 본문 소제목', encoding='utf-8')}"])
        self.client.post(f"{api}?token=tok-123", mixed, content_type="application/x-www-form-urlencoded")
        self.pl.refresh_from_db()
        self.assertEqual((self.pl.converted_title, self.pl.converted_tags, self.pl.converted_body),
                         ("자바 제목", "자바, 기초", "## 본문 소제목"))
        # 사실 점검 기록: 저장하고 변환 화면에 보인다 (출처 주소는 링크, 글은 이스케이프)
        check = "- 고침: 11/27 → 11/28 · 거래소 공지 · https://example.com/a?x=1&y=2\r\n- 미정: 12월 일정 · <아직 발표 없음>"
        self.client.post(f"{api}?token=tok-123", {"title": "t", "body": "b", "tags": "", "check": check})
        self.pl.refresh_from_db()
        self.assertTrue(self.pl.converted_check.startswith("- 고침: 11/27 → 11/28"))
        self.client.force_login(get_user_model().objects.get(username="tester"))
        res = self.client.get(reverse("site_templates:convert", args=[self.pl.pk]))
        self.assertContains(res, "사실 점검")
        self.assertContains(res, '<a href="https://example.com/a?x=1&amp;y=2" target="_blank" rel="noopener">')
        self.assertContains(res, "&lt;아직 발표 없음&gt;")

    def test_api_state_reads_with_token(self):
        """PC claude 가 매핑 번호·지난 변환본·컨셉을 읽는다 (2026-10-23, 발행한 글 고쳐 다시 보내기). 토큰이 있어야 한다"""
        from apps.core.models import ROUTINE_BRIEF_TOKEN_KEY, AppSetting
        AppSetting.set(ROUTINE_BRIEF_TOKEN_KEY, "tok")
        self.pl.converted_body = "지난 변환본"
        self.pl.save()
        url = reverse("site_templates:api_state")
        self.client.logout()
        self.assertEqual(self.client.get(url, {"token": "bad"}).status_code, 403)
        data = self.client.get(url, {"token": "tok", "site": "memorily"}).json()
        site = data["sites"][0]
        self.assertEqual((len(data["sites"]), site["name"]), (1, "memorily"))
        self.assertIn("개발자", site["template"]["tone"])
        self.assertIn("Java", [c["name"] for c in site["categories"]])
        pl = site["placements"][0]
        self.assertEqual((pl["id"], pl["title"], pl["converted_body"]), (self.pl.pk, "자바 정리", "지난 변환본"))

    def test_old_site_page_redirects(self):
        url = reverse("site_templates:site", args=[self.memorily.pk])
        self.assertRedirects(self.client.get(url), f'{reverse("site_templates:index")}?site={self.memorily.sel}',
                             fetch_redirect_response=False)

    def test_convert_flow(self):
        url = reverse("site_templates:convert", args=[self.pl.pk])
        res = self.client.get(url)
        self.assertContains(res, "자바 정리")
        self.assertIn("개발자 1인칭", res.context["request_text"])  # 요청문에 사이트 템플릿이 들어간다
        self.client.post(url, {"action": "request", "convert_note": "짧게", "converted_title": "", "converted_body": ""})
        self.pl.refresh_from_db()
        self.assertEqual((self.pl.convert_status, self.pl.convert_note), ("requested", "짧게"))
        data = self.client.get(reverse("site_templates:requests")).json()
        self.assertEqual(data["count"], 1)
        self.assertIn("짧게", data["items"][0]["prompt"])
        res = self.client.post(url, {"action": "save", "converted_title": "바꾼 제목", "converted_body": "바꾼 본문",
                                     "convert_note": "짧게"}, HTTP_X_REQUESTED_WITH="fetch")
        self.assertEqual(res.json(), {"ok": True, "status": "done"})
        self.pl.refresh_from_db()
        self.assertEqual((self.pl.convert_status, self.pl.converted_title), ("done", "바꾼 제목"))
        self.assertIsNotNone(self.pl.converted_at)
        self.client.post(url, {"action": "check", "converted_title": "바꾼 제목", "converted_body": "바꾼 본문", "convert_note": ""})
        self.pl.refresh_from_db()
        self.assertEqual(self.pl.convert_status, "checked")
        self.assertEqual(self.client.get(reverse("site_templates:requests")).json()["count"], 0)


class PasteFormatTests(TestCase):
    """플랫폼별 붙여넣기: 포맷 규칙(조사 결과)과 변환 화면의 복사 방식"""

    def setUp(self):
        user = get_user_model().objects.create_user("tester", password="pw-test-1234")
        self.client.force_login(user)
        self.post = Post.objects.create(title="원문", stage="post", body="본문")

    def place(self, blog_name, cat_name=None):
        blog = Blog.objects.get(name=blog_name)
        cat = SiteCategory.objects.filter(blog=blog, name=cat_name).first() if cat_name else None
        cat = cat or SiteCategory.objects.create(blog=blog, name="시험")
        return Placement.objects.create(site_category=cat, tistory_post=self.post, converted_title="바꾼 제목",
                                        converted_body="## 소제목\n\n**굵게** 본문", converted_tags="태그1, 태그2",
                                        convert_status="done")

    def test_guides_come_from_research(self):
        self.assertTrue(PlatformFormat.objects.get(platform="naver").guide.startswith("서식 그대로 붙인다"))  # 0007 에서 줄였다
        self.assertIn("HTML 보기", PlatformFormat.objects.get(platform="blogger").guide)

    def test_naver_paste_gaps_tags_and_check_date(self):
        """네이버 (2026-10-20 사용자): 문단 사이 빈 줄, 태그는 '#태그 #태그', 출처 줄 확인 날짜는 괄호 안 작은 회색"""
        pl = self.place("black_lukey", "낙서장")
        pl.converted_body = "첫 문단\n\n## 소제목\n\n둘째 문단\n\n참고: [출처](https://a.com) (2026년 10월 20일 확인)"
        pl.converted_tags = "태그1, 태그 2, #태그3"
        pl.save()
        res = self.client.get(reverse("site_templates:convert", args=[pl.pk]))
        rich = res.context["paste_html"]
        self.assertEqual(rich.count("&nbsp;</p>"), 5)  # 블록 네 개 사이에 빈 줄 하나씩, ## 소제목 앞만 셋
        self.assertEqual(res.context["converted_html"], rich)  # 미리보기도 붙여넣을 HTML 그대로
        self.assertIn('<span style="color:#999999;font-size:13px">(10.20 확인)</span>', rich)
        self.assertNotIn("2026년 10월 20일 확인", rich)
        self.assertIn("font-size:13px;line-height:1.8;margin:0;color:#999999\">참고: <a href=\"https://a.com\"", rich)  # 참고 줄은 작은 회색 (2026-10-23)
        self.assertEqual(rich.count("color:#999999"), 2)  # 참고 줄 + 확인 날짜만, 본문은 그대로
        from apps.writing.render import render_body, tistory_html
        self.assertIn('<p style="color:#999999;font-size:13px">참고:', tistory_html(render_body(pl.converted_body)))  # 티스토리도
        self.assertContains(res, f'<textarea id="st-tags-{pl.pk}" hidden>#태그1 #태그2 #태그3</textarea>', html=False)
        self.assertEqual(res.context["tag_items"], ["태그1", "태그2", "태그3"])  # 하나씩 복사 (태그 칸은 Enter 로 하나씩)
        self.assertContains(res, 'data-copy-text="태그2"')
        self.assertTrue(res.context["tag_bookmarklet"].startswith("javascript:"))
        self.assertNotIn(" ", res.context["tag_bookmarklet"])
        self.assertNotIn("#", res.context["tag_bookmarklet"])  # 주소에 # 이 있으면 뒤가 잘린다
        # 한 번에 넣기 (2026-10-27): 글자칸은 표시 + JSON, 서식칸은 본문 HTML. 북마크 하나가 세 사이트를 나눈다
        import json
        from .paste import ALL_MARK
        self.assertTrue(res.context["paste_all"].startswith(ALL_MARK))
        data = json.loads(res.context["paste_all"][len(ALL_MARK):])
        self.assertEqual((data["tags"], data["html"]), (["태그1", "태그2", "태그3"], rich))
        mark = res.context["paste_bookmarklet"]
        self.assertTrue(mark.startswith("javascript:"))
        self.assertNotIn(" ", mark)
        self.assertNotIn("#", mark)
        self.assertContains(res, f'data-copy-plain="#st-all-{pl.pk}"')
        self.assertNotContains(res, "네이버 태그 넣기</a>")  # 새 북마크가 태그도 넣는다
        tistory = self.place("memorily")
        res = self.client.get(reverse("site_templates:convert", args=[tistory.pk]))
        self.assertContains(res, f'<textarea id="st-tags-{tistory.pk}" hidden>태그1, 태그2</textarea>', html=False)  # 티스토리는 쉼표 그대로
        self.assertEqual(res.context["tag_items"], [])
        self.assertEqual(json.loads(res.context["paste_all"][len(ALL_MARK):])["tags"], ["태그1", "태그2"])
        self.assertNotIn("<p>&nbsp;</p>", res.context["paste_html"])  # 티스토리는 네이버식 빈 줄이 아니라 티스토리식 (data-ke-size)

    def test_wrapped_image_unwrapped_on_save(self):
        """그림 줄을 <div> 로 감싸면 마크다운이 풀리지 않아 주소가 글자로 보인다 (2026-10-27 코스피 시황 노트) → 저장할 때 벗긴다."""
        from apps.core.models import ROUTINE_BRIEF_TOKEN_KEY, AppSetting
        from .paste import unwrap_images
        AppSetting.set(ROUTINE_BRIEF_TOKEN_KEY, "tok")
        img = "![지수 카드](https://raw.githubusercontent.com/x/y.png)"
        self.assertEqual(unwrap_images(f'앞\n\n<div style="text-align:center">\n\n{img}\n\n</div>\n\n뒤'), f"앞\n\n{img}\n\n뒤")
        self.assertEqual(unwrap_images(f"<p>{img}\n*사진: 가 · Pexels*</p>"), f"{img}\n*사진: 가 · Pexels*")
        self.assertEqual(unwrap_images("<div>표</div>"), "<div>표</div>")  # 그림이 아니면 그대로
        pl = self.place("밤밤")
        self.client.post(reverse("site_templates:api_save", args=[pl.pk]) + "?token=tok",
                         {"body": f'첫 줄\n\n<div style="text-align:center">\n\n{img}\n\n</div>'})
        pl.refresh_from_db()
        self.assertEqual(pl.converted_body, f"첫 줄\n\n{img}")
        self.assertIn('<img', self.client.get(reverse("site_templates:convert", args=[pl.pk])).context["paste_html"])

    def test_planned_row_copy(self):
        """발행예정글 표의 '복사' (2026-10-27 사용자): 누르면 변환글 보기의 '한 번에 복사'와 같은 내용을 받는다. 워드프레스는 없다."""
        import json
        from .paste import ALL_MARK
        pl = self.place("memorily")
        wp = self.place("워드프레스")
        res = self.client.get(reverse("posts:planned"))
        self.assertContains(res, f'data-copy-url="{reverse("site_templates:paste_data", args=[pl.pk])}"')
        self.assertNotContains(res, reverse("site_templates:paste_data", args=[wp.pk]))
        d = self.client.get(reverse("site_templates:paste_data", args=[pl.pk])).json()
        page = self.client.get(reverse("site_templates:convert", args=[pl.pk])).context
        self.assertEqual((d["html"], d["plain"]), (page["paste_html"], page["paste_all"]))
        self.assertEqual(json.loads(d["plain"][len(ALL_MARK):])["title"], "바꾼 제목")
        self.assertIn("티스토리", d["msg"])
        self.assertEqual(self.client.get(reverse("site_templates:paste_data", args=[wp.pk])).status_code, 400)

    def test_naver_fixes_apply_to_html_saved_conversion(self):
        """HTML 로 저장한 변환본(예: 롤드컵 입문)도 빈 줄 · 확인 날짜가 같게. 다시 그려도 두 번 감싸지 않는다."""
        from apps.writing.render import render_body
        pl = self.place("black_lukey", "낙서장")
        pl.converted_body = "<p>LoL 공식 안내 기준, 한국 시간, 10월 15일 확인</p><h2>보는 법</h2><p>골드 차이</p>"
        pl.save()
        rich = self.client.get(reverse("site_templates:convert", args=[pl.pk])).context["paste_html"]
        self.assertEqual(rich.count("&nbsp;</p>"), 4)  # 소제목 앞 셋 + 뒤 하나
        self.assertEqual(rich.count("(10.15 확인)</span>"), 1)
        once = render_body(pl.converted_body)
        self.assertEqual(render_body(once), once)
        editor = self.place("black_lukey", "낙서장")
        editor.converted_body = "<p>가</p><p><br></p><p>나</p>"  # 네이버 편집기 꼴: 빈 줄이 이미 있다
        editor.save()
        rich = self.client.get(reverse("site_templates:convert", args=[editor.pk])).context["paste_html"]
        self.assertNotIn("&nbsp;</p>", rich)

    def test_naver_summary_quote_is_naver_quotation(self):
        """네이버 맨 위 결론 인용은 네이버 '따옴표' 인용구로 (2026-10-21 사용자). 미리보기도 그 모양, 티스토리는 세로줄 인용"""
        pl = self.place("black_lukey", "낙서장")
        pl.converted_body = "> 롤을 몰라도 롤드컵은 즐길 수 있어요.\n\n본문"
        pl.save()
        res = self.client.get(reverse("site_templates:convert", args=[pl.pk]))
        self.assertIn("<blockquote", res.context["paste_html"])
        self.assertContains(res, "st-converted st-naver")
        self.assertContains(res, "data-st-solo")  # 원문 접기 버튼 (2026-10-23 사용자: 변환본만 크게)
        self.assertContains(res, "따옴표")
        tistory = self.place("memorily")
        tistory.converted_body = pl.converted_body
        tistory.save()
        res = self.client.get(reverse("site_templates:convert", args=[tistory.pk]))
        self.assertIn('data-ke-style="style2"', res.context["paste_html"])

    def test_info_card_and_naver_photo_620(self):
        """정보 카드 (2026-10-23 사용자: 입장 마감·입장료 같은 건 서술 말고 보기 쉽게, 시간표와 다른 디자인) · 네이버 사진 620"""
        pl = self.place("black_lukey", "낙서장")
        pl.converted_body = ("![오죽헌](https://a.com/x.jpg)\n\n설명 문장\n\n::: 장소 | 오죽헌\n⏰ 관람 | 09:00~18:00\n"
                             "🎫 예약 | 현장 매표 · [공식 안내](https://gn.go.kr/a?b=1&c=2)\n:::\n\n| 시간 | 동선 |\n|---|---|\n| 오전 | KTX |")
        pl.save()
        rich = self.client.get(reverse("site_templates:convert", args=[pl.pk])).context["paste_html"]
        self.assertIn('style="width:620px;max-width:100%;height:auto"', rich)  # 사진은 가운데 620
        self.assertIn("background-color:#1f6f5c;color:#ffffff", rich)  # 카드 머리 칸 (장소 = 초록)
        self.assertIn(">가 볼 곳</td>", rich)
        self.assertIn(">오죽헌</td>", rich)
        self.assertIn(">⏰ 관람</td>", rich)
        self.assertIn('<a href="https://gn.go.kr/a?b=1&amp;c=2" target="_blank" rel="noopener">공식 안내</a>', rich)
        self.assertNotIn(":::", rich)
        self.assertIn("background:#f3f4f6", rich)  # 보통 표(시간표)는 그대로 회색 머리
        tistory = self.place("memorily")
        tistory.converted_body = "::: 작품 | 가능한 사랑\n📺 볼 곳 | 넷플릭스\n:::"
        tistory.save()
        html = self.client.get(reverse("site_templates:convert", args=[tistory.pk])).context["paste_html"]
        self.assertIn("background-color:#3b3a8c", html)  # 티스토리에도 같은 카드 (작품 = 남색)
        self.assertIn(">작품 정보</td>", html)
        pl.converted_body = "![포스터: 가능한 사랑](https://a.com/p.jpg)\n\n![풍경](https://a.com/x.jpg)"  # 포스터는 작게 300
        pl.save()
        rich = self.client.get(reverse("site_templates:convert", args=[pl.pk])).context["paste_html"]
        self.assertIn('alt="포스터: 가능한 사랑" style="width:300px;max-width:100%;height:auto"', rich)
        self.assertIn('alt="풍경" style="width:620px;max-width:100%;height:auto"', rich)
        tistory.converted_body = pl.converted_body
        tistory.save()
        html = self.client.get(reverse("site_templates:convert", args=[tistory.pk])).context["paste_html"]
        self.assertIn('<img width="300" src="https://a.com/p.jpg"', html)
        self.assertIn('<img width="620" src="https://a.com/x.jpg"', html)

    def test_black_lukey_category_concepts(self):
        """black_lukey 카테고리별 글 모양 (2026-10-23 사용자 피드백, 0008): 템플릿 · 요청문에 글 모양이 들어간다"""
        from importlib import import_module
        mig = import_module("apps.site_templates.migrations.0008_black_lukey_categories")
        blog = Blog.objects.get(name="black_lukey")
        self.assertIn("링크 자리", SiteTemplate.objects.get(blog=blog).rules)
        cat = SiteCategory.objects.create(blog=blog, name="지역 놀거리", concept=mig.PLACE)
        pl = Placement.objects.create(site_category=cat, tistory_post=self.post)
        text = prompt.build(pl)
        self.assertIn("이런 분께 맞아요", text)  # 빼라는 단락
        self.assertIn("::: 장소", text)
        self.assertIn("원문에 없어도 변환이 채우고 맞춘다", text)
        self.assertIn("너비 620", text)
        self.assertNotIn("예약·제휴 링크 자리는 원문 그대로 둔다", text)

    def test_tistory_paste_gaps_and_photo_width(self):
        """티스토리 (2026-10-22 사용자): 스킨이 문단 간격을 0 으로 둬서 답답하다 → 블록 사이 빈 줄, 사진은 가운데 620"""
        pl = self.place("memorily")
        pl.converted_body = "첫 문단\n\n## 소제목\n\n![사진](https://a.com/x.png)\n\n끝"
        pl.save()
        res = self.client.get(reverse("site_templates:convert", args=[pl.pk]))
        html = res.context["paste_html"]
        self.assertEqual(html.count('<p data-ke-size="size16">&nbsp;</p>'), 4)  # 소제목 앞 셋 · 바로 뒤에는 없이 · 사진 뒤 하나
        self.assertIn("첫 문단</p>\n" + '<p data-ke-size="size16">&nbsp;</p>' * 3 + "<h2>", html)
        # 사진 문단은 티스토리 가운데 정렬 버튼의 꼴로 (2026-10-25: 다른 style 이 섞이면 붙여넣을 때 정렬이 풀린다)
        self.assertIn('<h2>소제목</h2>\n<p style="text-align: center;" data-ke-size="size16"><img width="620" src="https://a.com/x.png"', html)
        self.assertContains(res, "st-converted st-flat")  # 미리보기도 같은 간격
        pl.converted_body = '<p>가</p><p><br></p><p>나</p>'  # 편집기 HTML 은 빈 줄이 이미 있다
        pl.save()
        self.assertNotIn("&nbsp;", self.client.get(reverse("site_templates:convert", args=[pl.pk])).context["paste_html"])

    def test_memorily_ai_heading_bar_and_concept(self):
        """memorily › AI (2026-10-23 사용자): 소제목 앞 빨간 세로 막대 (크기·말 그대로), 컨셉에 도구마다 사진 · 가공이미지"""
        from .views import HEADING_BAR
        pl = self.place("memorily", "AI")
        html = self.client.get(reverse("site_templates:convert", args=[pl.pk])).context["paste_html"]
        self.assertIn(f'<h2 style="{HEADING_BAR}">소제목</h2>', html)
        text = prompt.build(pl)
        self.assertIn("도구(## 소제목)마다 1장씩", text)
        self.assertIn("가공이미지", text)
        other = self.place("memorily", "기타")  # 다른 카테고리는 막대 없이
        self.assertIn("<h2>소제목</h2>", self.client.get(reverse("site_templates:convert", args=[other.pk])).context["paste_html"])

    def test_copy_buttons_follow_platform(self):
        res = self.client.get(reverse("site_templates:convert", args=[self.place("black_lukey", "낙서장").pk]))
        self.assertContains(res, 'data-copy-rich="#st-paste-')  # 네이버: 서식 그대로 (복사 칸 id 에 매핑 번호)
        self.assertIn("style=", res.context["paste_html"])  # 네이버는 인라인 style 을 단 서식 HTML
        tistory = self.place("memorily")
        tistory.converted_body = "| 항목 | 값 |\n|---|---|\n| 가 | **10%**를 |"
        tistory.save()
        res = self.client.get(reverse("site_templates:convert", args=[tistory.pk]))
        html = res.context["clean_html"]  # 티스토리: 티스토리 글쓰기와 같은 인라인 style HTML
        self.assertIn('<table style="border-collapse:collapse', html)
        self.assertNotIn("<th", html)  # 머리글 줄이 표 밖으로 빠지지 않게 보통 칸
        self.assertIn("<strong>10%</strong>를", html)
        self.assertEqual(res.context["paste_html"], html)
        res = self.client.get(reverse("site_templates:convert", args=[self.place("밤밤").pk]))
        self.assertContains(res, "본문 HTML (HTML 보기)")
        self.assertEqual(res.context["clean_html"],  # 블로거도 티스토리처럼 (소제목 바로 뒤는 빈 줄 없이)
                         '<h2>소제목</h2>\n<p><strong>굵게</strong> 본문</p>')
        res = self.client.get(reverse("site_templates:convert", args=[self.place("워드프레스").pk]))
        self.assertContains(res, 'data-copy="#st-raw-')  # 워드프레스: 마크다운 그대로
        wp_html = res.context["clean_html"]  # class HTML 을 사용자 정의 HTML 블록으로 (2026-10-26)
        self.assertTrue(wp_html.startswith("<!-- wp:html -->\n<style>"))  # 글모양 CSS 를 블록 안에 함께 (추가 CSS 없이도 같은 모양)
        self.assertTrue(wp_html.endswith('</style>\n<div class="jb-post" lang="ko">\n<h2 id="소제목">소제목</h2>\n'
                                         '<p><strong>굵게</strong> 본문</p>\n</div>\n<!-- /wp:html -->'))
        self.assertContains(res, "태그1, 태그2")
        self.assertIn("## 돌려줄 것", res.context["request_text"])
        self.assertIn("사용자 정의 HTML", res.context["request_text"])  # 그 플랫폼 포맷 규칙이 요청문에 들어간다

    def test_convert_keeps_original_and_fills_photos(self):
        # 변환은 원문이 기준 + 사진·그림 자리는 채우거나 지운다 (2026-10-21 사용자). 워드프레스는 사진 찾기 없이 자리만 지운다
        tistory = self.place("memorily")
        request_text = self.client.get(reverse("site_templates:convert", args=[tistory.pk])).context["request_text"]
        self.assertIn("## 변환 원칙 (원문이 기준)", request_text)
        self.assertIn("## 사진·그림 (변환이 끝까지 채운다", request_text)
        self.assertIn("원문에 자리가 없어도 글마다 두 가지를 판단한다", request_text)  # 사진 1장 · 가공이미지 (2026-10-22 사용자)
        self.assertIn("맞는 사진이 없으면 그 줄을 지운다", request_text)
        self.assertNotIn("못 찾았으면 [사진: 설명]", request_text)
        self.assertNotIn("## 글 다듬기", request_text)  # 원문을 다시 짜게 만들던 규칙
        naver = self.place("black_lukey", "낙서장")
        naver_text = self.client.get(reverse("site_templates:convert", args=[naver.pk])).context["request_text"]
        self.assertIn("## 사진·그림", naver_text)
        self.assertNotIn("사진 → 한두 줄 설명을 반복", naver_text)  # 원문을 다시 짜게 만들던 구성 (0007 에서 뺐다)
        nunip = self.client.get(reverse("site_templates:convert", args=[self.place("눈잎").pk])).context["request_text"]
        self.assertNotIn("### 구성", nunip)  # 빈 칸은 늘어놓지 않는다 (black_lukey 는 0008 에서 구성이 생겼다)
        self.assertIn("쇼핑커넥트", naver_text)
        self.assertEqual(PlatformFormat.objects.get(platform="naver").guide.count("\n"), 3)
        wordpress = self.place("워드프레스")
        wp_text = self.client.get(reverse("site_templates:convert", args=[wordpress.pk])).context["request_text"]
        self.assertIn("## 사진·그림", wp_text)  # 워드프레스도 사진을 넣는다 (0030, 2026-10-26 사용자)
        self.assertIn("[사진]·📷·[그림] 자리 줄은 변환본에 남기지 않는다", wp_text)
        # 찾아 넣은 사진 + 출처 캡션 → 붙여넣기 HTML 에 실제 이미지와 캡션
        tistory.converted_body = "글\n\n![병원 대기실](https://images.unsplash.com/photo-1?w=1200&q=80)\n*사진: 홍길동 · Unsplash*"
        tistory.save()
        html = self.client.get(reverse("site_templates:convert", args=[tistory.pk])).context["clean_html"]
        self.assertIn('<img width="620" src="https://images.unsplash.com/photo-1?w=1200&amp;q=80" alt="병원 대기실"', html)
        self.assertIn("사진: 홍길동 · Unsplash</span></p>", html)  # 티스토리: 캡션 색은 span (2026-10-25)


class BloggerLabelTests(TestCase):
    """블로거 라벨은 5개쯤 (2026-10-22 사용자: 태그를 그대로 붙여 라벨이 너무 많아졌다)."""

    def test_prompt_asks_five_labels_and_copy_keeps_five(self):
        from .views import _tags_for
        bambam = Blog.objects.get(name="밤밤")
        cat = SiteCategory.objects.create(blog=bambam, name="코스피")
        pl = Placement.objects.create(site_category=cat, tistory_post=Post.objects.create(title="코스피 글", body="본문"),
                                      converted_tags="코스피, 증시, 반도체, 외국인, 환율, 금리, 나스닥, 2026")
        text = prompt.build(pl)
        self.assertIn("## 블로거 라벨", text)
        self.assertIn("첫째는 넣을 카테고리 이름", text)
        self.assertEqual(_tags_for(pl), "코스피, 증시, 반도체, 외국인, 환율")
        pl.site_category = SiteCategory.objects.get(blog__name="눈잎", name="공모주")
        self.assertNotIn("## 블로거 라벨", prompt.build(pl))


class LocatorMapTests(TestCase):
    """해외여행 글 맨 위 위치 지도 (2026-10-27 사용자: 어디인지 감이 안 온다)."""

    def test_prompt_by_concept(self):
        import importlib
        from django.apps import apps as live_apps
        travel = SiteCategory.objects.create(blog=Blog.objects.get(name="밤밤"), name="해외여행")
        world = SiteCategory.objects.create(blog=Blog.objects.get(platform="wordpress"), name="World Travel",
                                            concept="순서: 리드 → `## Trip at a Glance` → Sources.")
        importlib.import_module("apps.blog_types.migrations.0037_travel_locator_map").forward(live_apps, None)
        travel.refresh_from_db()
        world.refresh_from_db()
        self.assertTrue(travel.concept.startswith("- 위치 지도: 맨 위 인용 바로 다음"))
        self.assertIn("순서: 리드 → 위치 지도 → `## Trip at a Glance`", world.concept)
        pl = Placement.objects.create(site_category=travel, tistory_post=Post.objects.create(title="홍콩 3박 4일", body="본문"))
        self.assertIn("## 위치 지도", prompt.build(pl))
        pl.site_category = SiteCategory.objects.create(blog=travel.blog, name="주식")
        self.assertNotIn("## 위치 지도", prompt.build(pl))
        # 0038: 사이트별 지도 모양까지 자세히 + 국내 지역 놀거리 (위치 지도 → 여는 말)
        local = SiteCategory.objects.filter(blog__platform="naver", name="지역 놀거리", parent=None).first() or \
            SiteCategory.objects.create(blog=Blog.objects.get(platform="naver"), name="지역 놀거리")
        local.concept = "지역 놀거리 글 모양\n- 순서: 맨 위 인용 상자(결론) → 공감 한 줄 → 하루 시간표 표 → 마무리.\n- 마무리: 서술형."
        local.save()
        importlib.import_module("apps.blog_types.migrations.0038_locator_map_concepts").forward(live_apps, None)
        for cat in (travel, world, local):
            cat.refresh_from_db()
        self.assertTrue(travel.concept.startswith("- 위치 지도 (2026-10-27 사용자: 어디인지 감이 안 온다): 맨 위 인용"))
        self.assertIn("서울에서 그 도시까지 점선", travel.concept)
        self.assertIn("N km from London", world.concept)
        self.assertNotIn("- 위치 지도: 맨 위", world.concept)
        lines = local.concept.split("\n")
        self.assertEqual(lines[1], "- 순서: 맨 위 인용 상자(결론) → 위치 지도 → 여는 말 → 하루 시간표 표 → 마무리.")
        self.assertTrue(lines[2].startswith("- 위치 지도 (2026-10-27 사용자)") and lines[3].startswith("- 여는 말"))
        self.assertEqual(lines[-1], "- 마무리: 서술형.")
        # 0039: 워드프레스 Korea Travel
        korea = SiteCategory.objects.filter(blog__platform="wordpress", name="Korea Travel", parent=None).first() or \
            SiteCategory.objects.create(blog=world.blog, name="Korea Travel")
        korea.concept = "순서: 리드 → `## {City} at a Glance` → Sources."
        korea.save()
        importlib.import_module("apps.blog_types.migrations.0039_korea_travel_locator_map").forward(live_apps, None)
        korea.refresh_from_db()
        self.assertTrue(korea.concept.startswith("순서: 리드 → 위치 지도 → `## {City} at a Glance`"))
        self.assertIn("우리나라 작은 지도", korea.concept)

    def test_photo_counts(self):
        """0041: 사진이 빠지지 않게 (2026-10-27 사용자: 선운산·로마). 컨셉에 장수, 요청문에 한국관광콘텐츠랩."""
        import importlib
        from django.apps import apps as live_apps
        wp = Blog.objects.get(platform="wordpress")
        mountain = SiteCategory.objects.filter(blog=wp, name="산과 캠핑", parent=None).first() or \
            SiteCategory.objects.create(blog=wp, name="산과 캠핑")
        mountain.concept = "글 모양\n- 사진: 그 산이 그 계절에 실제로 찍힌 무료 사진 2~4장. 경험은 쓰지 않는다."
        mountain.save()
        world = SiteCategory.objects.create(blog=wp, name="World Travel",
                                            concept="- 끝에 `Sources:`. 사진은 그 장소가 실제로 찍힌 무료 사진. 경험은 쓰지 않는다.")
        importlib.import_module("apps.blog_types.migrations.0041_photo_counts").forward(live_apps, None)
        mountain.refresh_from_db()
        world.refresh_from_db()
        self.assertIn("2~4장 — 꼭", mountain.concept)
        self.assertTrue(mountain.concept.endswith("경험은 쓰지 않는다."))
        self.assertIn("Day 마다 그날 주인공 장소 1~2장, 글 전체 4장 이상", world.concept)
        pl = Placement.objects.create(site_category=mountain, tistory_post=Post.objects.create(title="선운산", body="본문"))
        text = prompt.build(pl)
        self.assertIn("api.visitkorea.or.kr/hub/getTourPhotoInfo.do", text)
        self.assertIn('{"type":"photo"', text)  # f-string 중괄호가 한 겹으로
        self.assertIn("그 장수가 바닥이다", text)

    def test_hero_skips_locator(self):
        from .views import _hero
        fig = prompt.FIGURE_URL + "%EB%B3%80%ED%99%98%EA%B7%B8%EB%A6%BC/66/"
        body = (f"> 리드\n\n![Map: where Rome is]({fig}%EC%9C%84%EC%B9%98%EC%A7%80%EB%8F%84.png)\n\n"
                f"## Day 1\n\n![Colosseum]({fig}colosseum.jpg)")
        self.assertEqual(_hero(body), {"src": f"{fig}colosseum.jpg", "alt": "Colosseum"})
        self.assertIsNone(_hero(f"> 리드\n\n![지도]({fig}%EC%9C%84%EC%B9%98%EC%A7%80%EB%8F%84.png)"))


class PanelPublishTests(TestCase):
    """변환본 창의 '발행 완료' ('변환 화면 따로 열기' 자리, 2026-10-23 사용자)."""

    def setUp(self):
        self.client.force_login(get_user_model().objects.create_user("tester", password="pw-test-1234"))

    def test_publish_button_in_panel(self):
        post = Post.objects.create(title="발행할 글", body="본문", stage="post", target="눈잎")
        cat = SiteCategory.objects.get(blog__name="눈잎", name="공모주")
        pl = Placement.objects.create(site_category=cat, tistory_post=post, convert_status="done", converted_body="변환본")
        url = reverse("site_templates:panel") + f"?p=tistory:{post.pk}&next=/blog/posts/view/"
        res = self.client.get(url)
        self.assertNotContains(res, "변환 화면 따로 열기")
        self.assertContains(res, 'name="publish" value="done"')
        self.client.post(reverse("posts:bulk"), {"ids": f"tistory:{post.pk}", "publish": "done", "next": "/blog/posts/view/"})
        post.refresh_from_db(), pl.refresh_from_db()
        self.assertEqual((post.publish_status, pl.status), ("done", "published"))
        res = self.client.get(url)
        self.assertContains(res, 'name="publish" value="todo"')  # 되돌리기


    def test_publish_from_post_page_goes_back(self):
        post = Post.objects.create(title="돌아갈 글", body="본문", stage="post", target="눈잎")
        Placement.objects.create(site_category=SiteCategory.objects.get(blog__name="눈잎", name="공모주"), tistory_post=post)
        back = "/blog/posts/view/?stage=post&site=%EB%88%88%EC%9E%8E"
        res = self.client.get(reverse("site_templates:post"), {"p": f"tistory:{post.pk}", "back": back})
        self.assertContains(res, f'<input type="hidden" name="next" value="{back.replace("&", "&amp;")}">', html=False)


class YudiLookTests(TestCase):
    """눈잎 › 일본 여행 '유디 메모지' 글 모양 (2026-10-23 사용자: 내용이 아니라 글꼴·색·배치 같은 화면 짜임을 유디 블로그처럼)."""

    BODY = "\n".join([
        "> 11월에 처음 간사이를 가는 사람에게",
        "", "## 1. 공항에서 난바까지는 어떻게 가요?", "",
        "난카이 라피트를 타면", "**40분**이면 닿아요.", "", "==표는 미리 사 두세요==", "",
        "| 목차 |", "| --- |", "| 1. 공항 |", "",
        "::: 장소 | 오사카성 천수각", "⏰ 운영 시간 | 9:00~18:00", "💴 입장료 | 1,200엔", ":::", "",
        "![성](https://a.com/1.jpg)", "", "![정원](https://a.com/2.jpg)", "", "---", "", "끝",
    ])

    def test_japan_category_has_yudi_look(self):
        cat = SiteCategory.objects.get(blog__name="눈잎", name="일본 여행")
        self.assertEqual(cat.look, "yudi")  # 0023
        self.assertIn("화면 모양", cat.concept)
        # 0024: 컨셉은 앞으로 쓸 글의 공통 규칙 — 지금 있는 글(오사카 3박 4일)의 값이 예로 박혀 있지 않다 (2026-10-23 사용자)
        for word in ("난바", "라피트", "히가시야마", "860원"):
            self.assertNotIn(word, cat.concept)
        self.assertIn("지난 글의 일수·거점·순서를 옮겨 오지 않는다", cat.concept)
        self.assertNotEqual(SiteCategory.objects.get(blog__name="눈잎", name="공모주").look, "yudi")  # 다른 카테고리는 그대로

    def test_render_and_prompt(self):
        from .views import _render_for
        cat = SiteCategory.objects.get(blog__name="눈잎", name="일본 여행")
        pl = Placement.objects.create(site_category=cat, tistory_post=Post.objects.create(title="오사카", body="본문"))
        out = _render_for(pl, self.BODY)[1]
        self.assertTrue(out.startswith("<div style=\"font-family:'NanumSquare'"))
        self.assertIn("text-align:center;line-height:2", out)  # 가운데 정렬 문단
        # 2026-10-23 사용자: 짜임새는 그대로, 꾸밈에 비해 정적이던 글씨·색을 살린다 — 둥근 굵은 소제목 + 형광펜 밑칠, 코랄 포인트
        self.assertIn('“</p><h2 style="font-family:\'NanumSquareRound\'', out)  # 큰따옴표 + 둥근 굵은 소제목
        self.assertIn('<span style="background:linear-gradient(transparent 58%,#d9f99d 58%);padding:0 4px">1.', out)  # 소제목 형광펜 밑칠
        self.assertIn("color:#ff7a59", out)  # 따옴표·나눔표는 코랄
        self.assertIn('<strong style="font-weight:700;color:#009d91">40분</strong>', out)  # 굵게 → 청록 굵게
        self.assertIn('<span style="background:linear-gradient(transparent 58%,#d9f99d 58%);font-weight:700">표는 미리 사 두세요</span>', out)  # 형광펜
        self.assertIn("border:3px solid #bfe9e3", out)  # 메모지 상자
        self.assertIn("⏰ 운영 시간 : 9:00~18:00", out)
        self.assertIn("background-color:#d9f99d;color:#00756c;padding:11px 16px", out)  # 목차 머리 칸 연두
        self.assertEqual(out.count("width:50%"), 2)  # 사진 두 장 → 콜라주 한 줄
        # 사진 크기 고정 (2026-10-23 사용자: 일상 사진이 너무 크다) — 콜라주 620 폭 · 칸 높이 240
        self.assertIn("width:620px;max-width:100%;border-collapse:separate", out)
        self.assertEqual(out.count("height:240px;object-fit:cover"), 2)
        one = _render_for(pl, "![성](https://a.com/1.jpg)")[1]  # 한 장은 620 × 400 (스킨 기본 style·width 를 덮는다)
        self.assertIn('<img style="display:block;width:620px;max-width:100%;height:400px;object-fit:cover', one)
        self.assertNotIn('width="620"', one)
        self.assertIn("• • •", out)  # --- → 나눔표
        self.assertNotIn('data-ke-size="size16">&nbsp;', out)
        self.assertIn("유디 메모지", prompt.build(pl))
        pl.site_category = SiteCategory.objects.get(blog__name="눈잎", name="공모주")
        self.assertNotIn("border:3px solid #bfe9e3", _render_for(pl, self.BODY)[1])  # 공모주·정책은 그대로
        self.assertNotIn("유디 메모지", prompt.build(pl))

    def test_daily_uses_same_look_for_products(self):
        """눈잎 › 일상도 같은 유디 메모지 (0025, 2026-10-23 사용자: 일상은 대부분 제품 소개 — 여행지 형태가 아니라 테마·구조·CSS 그대로)"""
        from importlib import import_module

        from django.apps import apps as django_apps

        from .views import _render_for
        daily = SiteCategory.objects.get(blog__name="눈잎", name="일상")
        self.assertEqual(daily.look, "yudi")
        self.assertNotIn("제품 소개 글 모양", daily.concept)  # 0028: 제품소개는 지웠다 (2026-10-26 사용자), 화면 모양은 둔다
        self.assertIn("화면 모양", daily.concept)
        body = "## 1. 어떤 가습기가 좋을까요?\n\n### 가습기 A\n\n::: 제품 | 가습기 A\n💰 가격 | 59,000원\n:::\n"
        post = Post.objects.create(title="가습기", body="원문", stage="post")
        pl = Placement.objects.create(site_category=daily, tistory_post=post, converted_body=body, convert_status="done")
        out = _render_for(pl, body)[1]
        self.assertIn("NanumSquareRound", out)
        self.assertIn("border:3px solid #bfe9e3", out)  # 제품 카드 → 메모지 상자
        self.assertIn("💰 가격 : 59,000원", out)
        self.assertIn("유디 메모지", prompt.build(pl))
        # 지금 발행예정인 일상 글은 변환 요청 + '이 글만' 으로 → '다시' 한 번이면 지난 변환본을 새 모양으로 고친다
        import_module("apps.blog_types.migrations.0025_nunip_daily_yudi").forward(django_apps, None)
        pl.refresh_from_db()
        self.assertEqual(pl.convert_status, "requested")
        self.assertIn("유디 메모지", pl.convert_note)
        launch = prompt.launcher(RequestFactory().get("/"), [pl], "tok")
        self.assertIn("## 지난 변환본 (사진·사실 점검은 살리고", launch)
        self.assertIn("::: 제품 | 가습기 A", launch)


class CloudConvertApiTests(TestCase):
    """클라우드 claude 가 토큰으로 글 관리의 글을 읽고, 카테고리에 넣고, 변환 안내문을 받는다 (2026-10-25)"""

    def setUp(self):
        from apps.core.models import ROUTINE_BRIEF_TOKEN_KEY, AppSetting
        AppSetting.set(ROUTINE_BRIEF_TOKEN_KEY, "tok")

    @override_settings(WRITING_DRAFTS_DIR="/없는-원고-폴더")
    def test_list_place_and_prompt(self):
        from apps.blog_types.models import Placement, SiteCategory
        from apps.writing.models import Post
        post = Post.objects.create(title="임시 원고", body="본문", stage="temp")
        cat = SiteCategory.objects.filter(blog__name="눈잎").first()
        self.assertEqual(self.client.get(reverse("site_templates:api_posts")).status_code, 403)
        res = self.client.get(reverse("site_templates:api_posts"), {"token": "tok"})
        row = next(p for p in res.json()["posts"] if p["ref"] == f"tistory:{post.pk}")
        self.assertEqual((row["stage"], row["placements"]), ("temp", []))
        url = reverse("site_templates:api_place") + "?token=tok"
        res = self.client.post(url, {"post": f"tistory:{post.pk}", "site_category": cat.pk}).json()
        post.refresh_from_db()
        self.assertEqual(post.stage, "review")  # 변환은 검토글부터라 옮긴다
        pl = Placement.objects.get(pk=res["id"])
        self.assertEqual((pl.site_category, pl.convert_status), (cat, "requested"))
        self.assertTrue(res["prompt"].startswith("# 사이트 변환"))
        self.assertIn(reverse("site_templates:api_save", args=[pl.pk]), res["prompt"])
        again = self.client.post(url, {"post": f"tistory:{post.pk}", "site_category": cat.pk}).json()
        self.assertEqual((again["id"], again["created"]), (pl.pk, False))  # 이미 넣은 곳은 그대로
        self.assertEqual(self.client.post(reverse("site_templates:api_place"), {"post": f"tistory:{post.pk}",
                                                                                "site_category": cat.pk}).status_code, 403)

    @override_settings(WRITING_DRAFTS_DIR="/없는-원고-폴더")
    def test_stage_move(self):
        from apps.writing.models import Post
        post = Post.objects.create(title="검토 원고", body="본문", stage="review")
        url = reverse("site_templates:api_stage") + "?token=tok"
        self.assertEqual(self.client.post(url, {"post": f"tistory:{post.pk}", "to": "post"}).json()["stage"], "post")
        post.refresh_from_db()
        self.assertEqual(post.stage, "post")
        self.assertEqual(self.client.post(url, {"post": f"tistory:{post.pk}", "to": "post"}).json()["stage"], "post")  # 이미 그 단계
        self.assertEqual(self.client.post(url, {"post": f"tistory:{post.pk}", "to": "temp"}).status_code, 400)  # 되돌릴 때는 이웃 단계만
        temp = Post.objects.create(title="임시", body="b", stage="temp")
        self.assertEqual(self.client.post(url, {"post": f"tistory:{temp.pk}", "to": "post"}).json()["stage"], "post")  # 임시 → 발행예정은 바로 (2026-10-27)
        self.assertEqual(self.client.post(reverse("site_templates:api_stage"), {"post": f"tistory:{post.pk}", "to": "review"}).status_code, 403)


class TistoryAlignTests(TestCase):
    def test_caption_and_blogger(self):
        """티스토리: 사진·캡션 문단은 style="text-align: center;" 하나 + 캡션 색은 span. 블로거는 그대로"""
        from apps.writing.render import render_body, tistory_align, tistory_html
        html = tistory_html(render_body("![사진](https://a.com/x.png)\n*사진: 누구 · Unsplash*\n\n끝"))
        out = tistory_align(html)
        self.assertIn('<p style="text-align: center;" data-ke-size="size16"><img width="620"', out)
        self.assertIn('<p style="text-align: center;" data-ke-size="size16"><span style="color: #6b7280; font-size: 14px;">사진: 누구 · Unsplash</span></p>', out)
        self.assertNotIn("margin:18px 0", out)
        self.assertNotIn("margin-top:-8px", out)
        self.assertEqual(tistory_align(out), out)  # 두 번 해도 같다


class WordpressLookTests(TestCase):
    """워드프레스 글 모양 (2026-10-26 사용자): class HTML + 글모양 CSS. 카드·목차·날짜 머리·다른 언어 요약·사진 캡션."""

    BODY = "\n".join([
        "> 3 days is enough for Taipei.", "", "## Day 1 · Old Town", "Walk.", "", "## Day 2 · Beitou", "Soak.", "",
        "## Day 3 · Jiufen", "Tea.", "", "## Budget", "| Item | Cost |", "|---|---|", "| MRT | TWD 50 |", "",
        "![Taipei 101](https://images.unsplash.com/photo-1?w=1200)", "*Photo: Someone · Unsplash*", "",
        "::: Place | Taipei 101", "⏰ Hours | 10:00–21:00", "📍 Map | [Google Maps](https://www.google.com/maps/search/?api=1&query=Taipei+101)", ":::",
        "", "## 日本語まとめ", "台北3日間。", "", "## 中文简介", "台北三日游。", "", "Sources: [Taiwan Tourism](https://eng.taiwan.net.tw)",
    ])

    def test_render_classes(self):
        from . import wp_looks
        out = wp_looks.render(self.BODY, "wp_travel")
        self.assertTrue(out.startswith('<div class="jb-post jb-travel" lang="en">'))
        self.assertIn('<blockquote class="jb-lead">', out)
        self.assertIn('<nav class="jb-toc"><p class="jb-toc__title">Contents</p>', out)  # 소제목 4개 이상 → 목차, 영어 글은 Contents
        self.assertIn('class="jb-day"', out)
        self.assertIn('<div class="jb-card jb-card--place">', out)
        self.assertIn('<span class="jb-card__kind">Place</span>', out)
        self.assertIn('target="_blank" rel="noopener">Google Maps</a>', out)
        self.assertIn('<figure class="jb-photo"><img src="https://images.unsplash.com/photo-1?w=1200" alt="Taipei 101" loading="lazy">'
                      '<figcaption>Photo: Someone · Unsplash</figcaption></figure>', out)
        self.assertIn('<div class="jb-table"><table>', out)
        self.assertEqual(out.count('<section class="jb-lang">'), 2)
        self.assertNotIn("日本語まとめ</a>", out)  # 다른 언어 요약은 목차에 넣지 않는다
        self.assertIn('<p class="jb-source">', out)
        self.assertNotIn("style=", out)  # 블록 에디터가 지우는 인라인 style 은 쓰지 않는다

    def test_convert_screen_for_wordpress(self):
        from apps.writing.models import Post
        wp = Blog.objects.get(platform="wordpress")
        cat = SiteCategory.objects.get(blog=wp, name="산과 캠핑")
        cat.look = "wp_mountain"
        cat.save()
        post = Post.objects.create(title="원문", stage="post", body="본문")
        pl = Placement.objects.create(site_category=cat, tistory_post=post, converted_title="민둥산 억새",
                                      converted_body="> 리드\n\n::: 코스 | 증산초교 코스\n⏱️ 시간 | 3시간\n:::", convert_status="done")
        self.client.force_login(get_user_model().objects.create_user("tester", password="pw-test-1234"))
        ctx = self.client.get(reverse("site_templates:convert", args=[pl.pk])).context
        self.assertIn("</style>\n<div class=\"jb-post jb-mountain\" lang=\"ko\">", ctx["clean_html"])
        self.assertIn('<span class="jb-card__kind">등산 코스</span>', ctx["clean_html"])
        self.assertIn(".jb-post.jb-mountain", ctx["converted_html"])  # 미리보기는 글모양 CSS 와 함께
        style = ctx["clean_html"].split("<style>", 1)[1].split("</style>", 1)[0]  # 붙일 HTML 에도 같은 CSS (주석·빈칸만 걷어 냄)
        self.assertIn(".jb-post.jb-mountain{", style)
        self.assertIn("Pretendard", style)
        self.assertNotIn("/*", style)
        self.assertIn("## 워드프레스 글 모양", ctx["request_text"])
        self.assertIn("코드 편집기", ctx["paste"]["where"])


class HeroPhotoTests(TestCase):
    """워드프레스 대표 사진 내려받기 (2026-10-26 사용자): 대표 이미지는 미디어 라이브러리에 올려야 해서 첫 사진을 파일로."""

    def setUp(self):
        import tempfile
        from pathlib import Path
        self.client.force_login(get_user_model().objects.create_user("tester", password="pw-test-1234"))
        wp = Blog.objects.get(platform="wordpress")
        cat = SiteCategory.objects.filter(blog=wp).first()
        self.post = Post.objects.create(title="원문", stage="post", body="본문")
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        fig = Path(self.tmp.name) / prompt.FIGURE_DIR / "57"
        fig.mkdir(parents=True)
        (fig / "mindungsan-station.jpg").write_bytes(b"\xff\xd8jpeg")
        self.pl = Placement.objects.create(site_category=cat, tistory_post=self.post, converted_title="민둥산", convert_status="done",
                                           converted_body="> 리드\n\n![민둥산역 승강장](" + prompt.FIGURE_URL
                                           + "%EC%BD%98%ED%85%90%EC%B8%A0/%EB%B8%94%EB%A1%9C%EA%B7%B8_%EC%B9%B4%ED%8E%98/"
                                           "%EB%B3%80%ED%99%98%EA%B7%B8%EB%A6%BC/57/mindungsan-station.jpg)\n*사진: 한국관광공사*\n\n"
                                           "![둘째](https://images.unsplash.com/photo-2?w=620)")

    def url(self, pl=None):
        return reverse("site_templates:hero_photo", args=[(pl or self.pl).pk])

    def test_button_on_wordpress_convert_screen(self):
        res = self.client.get(reverse("site_templates:convert", args=[self.pl.pk]))
        self.assertContains(res, self.url())
        self.assertContains(res, 'data-copy-text="민둥산역 승강장"')  # 대체 텍스트 복사
        tistory = Placement.objects.create(site_category=SiteCategory.objects.filter(blog__platform="tistory").first(),
                                           tistory_post=self.post, converted_body="![가](https://images.unsplash.com/photo-1)",
                                           convert_status="done")
        self.assertNotContains(self.client.get(reverse("site_templates:convert", args=[tistory.pk])), "대표 사진")

    def test_repo_figure_served_from_disk(self):
        with override_settings(REPO_ROOT=self.tmp.name):
            res = self.client.get(self.url())
        self.assertEqual(res.status_code, 200)
        self.assertIn('attachment; filename="mindungsan-station.jpg"', res["Content-Disposition"])
        self.assertEqual(b"".join(res.streaming_content), b"\xff\xd8jpeg")

    def test_outside_figure_dir_not_served(self):
        from unittest import mock
        self.pl.converted_body = f"![x]({prompt.FIGURE_URL}workspace/db.sqlite3)"
        self.pl.save()
        with override_settings(REPO_ROOT=self.tmp.name), mock.patch("urllib.request.urlopen", side_effect=OSError):
            res = self.client.get(self.url())
        self.assertEqual(res.status_code, 302)  # 저장소의 다른 파일은 내주지 않는다

    def test_remote_photo_fetched_or_redirected(self):
        from unittest import mock
        self.pl.converted_body = "![억새](https://images.unsplash.com/photo-123abc?w=620)"
        self.pl.save()
        res_obj = mock.MagicMock()
        res_obj.__enter__.return_value = res_obj
        res_obj.headers.get_content_type.return_value = "image/jpeg"
        res_obj.read.return_value = b"img"
        with mock.patch("urllib.request.urlopen", return_value=res_obj):
            res = self.client.get(self.url())
        self.assertEqual(res.content, b"img")
        self.assertIn('filename="photo-123abc.jpg"', res["Content-Disposition"])
        with mock.patch("urllib.request.urlopen", side_effect=OSError):  # 서버가 못 받으면 사진 주소로 (브라우저에서 저장)
            res = self.client.get(self.url())
        self.assertRedirects(res, "https://images.unsplash.com/photo-123abc?w=620", fetch_redirect_response=False)

    def test_no_photo_404(self):
        self.pl.converted_body = "사진 없음"
        self.pl.save()
        self.assertEqual(self.client.get(self.url()).status_code, 404)


class ConvertSendByFileTests(TestCase):
    """변환본 보내기: 제목·태그도 파일로 (2026-10-26: Windows 명령줄이 cp949 라 제목의 — 가 ? 로 서버에 들어갔다)."""

    def test_launcher_sends_title_and_tags_from_files(self):
        wp = Blog.objects.get(platform="wordpress")
        cat = SiteCategory.objects.filter(blog=wp).first()
        post = Post.objects.create(title="원문 — 제목", stage="post", body="본문")
        pl = Placement.objects.create(site_category=cat, tistory_post=post)
        launch = prompt.launcher(RequestFactory().get("/"), [pl], "tok")
        self.assertIn(f'--data-urlencode "title@workspace/.routine/convert/{pl.pk}-title.txt"', launch)
        self.assertIn(f'--data-urlencode "tags@workspace/.routine/convert/{pl.pk}-tags.txt"', launch)
        self.assertNotIn("title=<제목>", launch)

    def test_title_file_keeps_dash(self):
        from urllib.parse import quote_plus
        from apps.core.models import ROUTINE_BRIEF_TOKEN_KEY, AppSetting
        AppSetting.set(ROUTINE_BRIEF_TOKEN_KEY, "tok")
        cat = SiteCategory.objects.filter(blog__platform="wordpress").first()
        pl = Placement.objects.create(site_category=cat, tistory_post=Post.objects.create(title="t", stage="post", body="b"))
        body = "&".join(f"{k}={quote_plus(v)}" for k, v in [("title", "민둥산 억새 — 증산초\n"), ("tags", "억새, 민둥산\n"), ("body", "본문")])
        self.client.post(reverse("site_templates:api_save", args=[pl.pk]) + "?token=tok", body, content_type="application/x-www-form-urlencoded")
        pl.refresh_from_db()
        self.assertEqual((pl.converted_title, pl.converted_tags), ("민둥산 억새 — 증산초", "억새, 민둥산"))  # 파일 끝 줄바꿈은 걷는다


class WordpressDraftTests(TestCase):
    """워드프레스 초안 자동 올리기 (2026-10-26 사용자): 서버 api_wp 재료 → PC wp_draft 가 REST API 로 초안 → 글 번호를 돌려준다."""

    BODY = ("> 증산초 코스는 완만하고 3.2km예요. **11월 8일**까지 축제.\n> 셔틀은 멈췄어요.\n\n## 코스\n본문\n\n"
            "![민둥산 억새](https://images.unsplash.com/photo-9?w=620)\n*사진: 누구 · Unsplash*")

    def setUp(self):
        from apps.core.models import ROUTINE_BRIEF_TOKEN_KEY, AppSetting
        AppSetting.set(ROUTINE_BRIEF_TOKEN_KEY, "tok")
        self.cat = SiteCategory.objects.get(blog__platform="wordpress", name="산과 캠핑")
        self.pl = Placement.objects.create(site_category=self.cat, tistory_post=Post.objects.create(title="원문", stage="post", body="b"),
                                           converted_title="민둥산 억새 등산코스 — 증산초", converted_body=self.BODY,
                                           converted_tags="민둥산, 억새", convert_status="done")
        self.api = reverse("site_templates:api_wp", args=[self.pl.pk]) + "?token=tok"

    def test_helpers(self):
        from . import wp_looks
        self.assertEqual(wp_looks.excerpt(self.BODY), "증산초 코스는 완만하고 3.2km예요. 11월 8일까지 축제. 셔틀은 멈췄어요.")
        self.assertEqual(wp_looks.excerpt("## 소제목\n\n첫 문단이에요.\n\n둘째"), "첫 문단이에요.")  # 리드가 없으면 첫 문단
        self.assertEqual(wp_looks.auto_slug("3 Days in Kyoto (Nov 2026): Autumn Leaves + Tax-Free Rules"),
                         "3-days-in-kyoto-autumn-leaves-tax-free")
        self.assertEqual(wp_looks.auto_slug("민둥산 억새"), "")  # 한글 제목은 변환이 준다
        self.assertEqual(wp_looks.clean_slug(" Mindungsan  Silver_Grass! "), "mindungsan-silver-grass")

    def test_api_wp(self):
        self.assertEqual(self.client.get(reverse("site_templates:api_wp", args=[self.pl.pk]) + "?token=bad").status_code, 403)
        save = reverse("site_templates:api_save", args=[self.pl.pk]) + "?token=tok"
        self.client.post(save, {"title": self.pl.converted_title, "body": self.BODY, "slug": "Mindungsan Silver-Grass Hiking\n"})
        data = self.client.get(self.api).json()
        self.assertEqual(data["slug"], "mindungsan-silver-grass-hiking")
        self.assertEqual((data["title"], data["category"], data["tags"]), ("민둥산 억새 등산코스 — 증산초", "산과 캠핑", ["민둥산", "억새"]))
        self.assertTrue(data["content"].startswith("<!-- wp:html -->\n<style>"))
        self.assertEqual(data["hero"], {"src": "https://images.unsplash.com/photo-9?w=620", "alt": "민둥산 억새"})
        self.assertIn("셔틀은 멈췄어요", data["excerpt"])
        self.assertIsNone(data["wp_post_id"])
        self.assertEqual(self.client.post(self.api, {"wp_post_id": "77"}).content.decode(), f"ok {self.pl.pk} wp 77")
        self.pl.refresh_from_db()
        self.assertEqual(self.pl.wp_post_id, 77)
        tistory = Placement.objects.create(site_category=SiteCategory.objects.filter(blog__platform="tistory").first(),
                                           tistory_post=self.pl.tistory_post, converted_body="b")
        self.assertEqual(self.client.get(reverse("site_templates:api_wp", args=[tistory.pk]) + "?token=tok").status_code, 400)
        # 변환 화면에 초안 열기
        self.client.force_login(get_user_model().objects.create_user("tester", password="pw-test-1234"))
        self.assertContains(self.client.get(reverse("site_templates:convert", args=[self.pl.pk])), "wp-admin/post.php?post=77&amp;action=edit")

    def test_launcher_adds_slug_and_draft_for_wordpress(self):
        launch = prompt.launcher(RequestFactory().get("/"), [self.pl], "tok")
        self.assertIn(f'--data-urlencode "slug@workspace/.routine/convert/{self.pl.pk}-slug.txt"', launch)
        self.assertIn(f'manage.py wp_draft "http://testserver/blog/site-templates/api/wp/{self.pl.pk}/?token=tok"', launch)
        tistory = Placement.objects.create(site_category=SiteCategory.objects.filter(blog__platform="tistory").first(),
                                           tistory_post=self.pl.tistory_post)
        self.assertNotIn("wp_draft", prompt.launcher(RequestFactory().get("/"), [tistory], "tok"))
        from apps.routines.local_run import ROUTINE_ALLOW
        self.assertIn("Bash(workspace/.venv/Scripts/python.exe workspace/manage.py wp_draft *)", ROUTINE_ALLOW)

    def test_draft_flow(self):
        from unittest import mock
        from . import wp_rest

        class Fake(wp_rest.Client):
            def __init__(self, existing=None):
                super().__init__("https://jinbaam.com", "u", "p")
                self.calls, self.existing = [], existing

            def call(self, method, path, data=None, raw=None, headers=None):
                self.calls.append((method, path, data))
                if path.startswith("/categories"):
                    return [{"id": 2, "name": "산과 캠핑"}, {"id": 3, "name": "드라이브&middot;자동차"}]
                if path.startswith("/tags?"):
                    return [{"id": 9, "name": "민둥산"}] if "%EB%AF%BC" in path else []
                if path == "/tags":
                    return {"id": 10}
                if path == "/media":
                    return {"id": 55}
                if path.startswith("/media/"):
                    return {}
                if path.startswith("/posts/") and method == "GET":
                    if self.existing is None:
                        raise wp_rest.WPError("404 rest_post_invalid_id")
                    return self.existing
                return {"id": 100 if path == "/posts" else int(path.split("/")[2])}

        job = {"id": self.pl.pk, "title": "t", "content": "<!-- wp:html -->x", "category": "산과 캠핑", "tags": ["민둥산", "억새"],
               "slug": "mindungsan", "excerpt": "e", "hero": {"src": "https://x/p.jpg", "alt": "억새"}, "wp_post_id": None}
        with mock.patch.object(wp_rest, "fetch_job", return_value=job), mock.patch.object(wp_rest, "report") as rep, \
                mock.patch.object(wp_rest, "image_bytes", return_value=(b"img", "p.jpg", "image/jpeg")):
            fake = Fake()
            out = wp_rest.draft("http://srv/api", fake, log=lambda m: None)
            self.assertIn("워드프레스 초안 100 새로 만듦", out)
            post = next(d for m, p, d in fake.calls if p == "/posts")
            self.assertEqual((post["status"], post["categories"], post["tags"], post["featured_media"], post["slug"]),
                             ("draft", [2], [9, 10], 55, "mindungsan"))
            rep.assert_called_with("http://srv/api", 100)
            # 다시 변환: 초안이면 같은 글을 고친다 (대표 이미지가 이미 있으면 다시 올리지 않는다)
            job["wp_post_id"] = 100
            fake = Fake(existing={"status": "draft", "featured_media": 55})
            out = wp_rest.draft("http://srv/api", fake, log=lambda m: None)
            self.assertIn("워드프레스 초안 100 고침", out)
            self.assertFalse(any(p == "/media" for m, p, d in fake.calls))
            # 발행한 글은 건드리지 않는다
            fake = Fake(existing={"status": "publish"})
            self.assertIn("건너뜀", wp_rest.draft("http://srv/api", fake, log=lambda m: None))
            self.assertFalse(any(m == "POST" for m, p, d in fake.calls))

    def test_command_skips_without_password(self):
        from io import StringIO
        from unittest import mock
        from django.core.management import call_command
        out = StringIO()
        with mock.patch.dict("os.environ", {"WP_USER": "", "WP_APP_PASSWORD": ""}):
            call_command("wp_draft", "http://srv/api", stdout=out)
        self.assertIn("건너뜀", out.getvalue())
