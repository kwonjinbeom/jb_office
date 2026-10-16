"""블로그 글 분류: 대분류 › 카테고리 › 타입 › 하위.

대분류 = 분류의 목적. 첫째는 '판매 수익 (커넥트)': 블로그에 표시하는 카테고리가 아니라
         쇼핑커넥트·쿠팡파트너스 수익을 위한 방향이다. 일상·맛집 같은 블로그 표시 분류는 다른 대분류로 둔다.
카테고리 = (판매 수익에서는) 사게 만드는 방향 (A 문제 해결 ~ G 여행·체험). 나누는 기준은 '글을 연 사람의 질문'이다.
타입 = 그 방향 안에서 매번 같은 틀로 물건만 바꿔 쓰는 글 모양.
하위 = 타입을 실제로 나눠 쓰는 단위 (품목군·대상·변형 등).
처음 값과 짠 이유: 콘텐츠/블로그_카페/포스팅자동화/08_수익형_카테고리.md
"""
from django.db import models
from apps.core.models import TrashableModel


class Section(TrashableModel):
    name = models.CharField("대분류", max_length=40)
    note = models.TextField("설명", blank=True, help_text="이 대분류가 무엇을 위한 분류인지")
    order = models.PositiveIntegerField("순서", default=0)

    class Meta:
        ordering = ["order", "pk"]

    def __str__(self):
        return self.name

    @property
    def sel(self):
        return f"g{self.pk}"


class Category(TrashableModel):
    class Platform(models.TextChoices):
        ALL = "all", "공통"
        NAVER = "naver", "네이버"
        TISTORY = "tistory", "티스토리"

    section = models.ForeignKey(Section, verbose_name="대분류", on_delete=models.CASCADE, related_name="categories")
    code = models.CharField("기호", max_length=4, help_text="A, B, C …")
    name = models.CharField("카테고리", max_length=40)
    direction = models.CharField("방향", max_length=120, blank=True,
                                 help_text="판매 수익: 사게 만드는 방향 (불편 → 해결템) · 광고 수익: 사람들이 찾아오는 이유")
    question = models.CharField("독자의 질문", max_length=160, blank=True,
                                help_text="글을 연 사람이 검색창에 치는 질문. 이 질문으로 카테고리가 갈린다")
    platform = models.CharField("플랫폼", max_length=10, choices=Platform.choices, default=Platform.ALL)
    note = models.TextField("설명", blank=True)
    order = models.PositiveIntegerField("순서", default=0)

    class Meta:
        ordering = ["order", "code", "pk"]

    def __str__(self):
        return f"{self.code}. {self.name}"

    @property
    def sel(self):
        return f"c{self.pk}"


class PostType(TrashableModel):
    category = models.ForeignKey(Category, verbose_name="카테고리", on_delete=models.CASCADE, related_name="types")
    name = models.CharField("타입", max_length=60)
    skeleton = models.CharField("쓰는 뼈대", max_length=80, blank=True,
                                help_text="07 템플릿화 분석 4절의 뼈대. 예: B. 비교·고르기형")
    examples = models.TextField("예시 제목", blank=True, help_text="한 줄에 하나")
    note = models.TextField("설명", blank=True)
    order = models.PositiveIntegerField("순서", default=0)

    class Meta:
        ordering = ["order", "pk"]

    def __str__(self):
        return f"{self.category.code} › {self.name}"

    @property
    def sel(self):
        return f"t{self.pk}"

    @property
    def example_list(self):
        return [line.strip() for line in self.examples.splitlines() if line.strip()]


class SubType(TrashableModel):
    post_type = models.ForeignKey(PostType, verbose_name="타입", on_delete=models.CASCADE, related_name="subs")
    name = models.CharField("하위", max_length=80)
    note = models.TextField("설명", blank=True, help_text="이 하위로 쓸 때의 품목·대상·주의점 등")
    order = models.PositiveIntegerField("순서", default=0)

    class Meta:
        ordering = ["order", "pk"]

    def __str__(self):
        return f"{self.post_type} › {self.name}"

    @property
    def sel(self):
        return f"s{self.pk}"


class SiteCategory(TrashableModel):
    """실제 사이트(운영 화면의 블로그)에 있는 카테고리 이름. 사이트 › 카테고리 › 하위 카테고리 (티스토리·네이버 모두 2단).

    위의 대분류·카테고리는 글을 나누는 기준이고, 이것은 각 블로그에 지금 실제로 걸려 있는 메뉴 이름이다.
    """
    blog = models.ForeignKey("blog_rules.Blog", verbose_name="사이트", on_delete=models.CASCADE, related_name="site_categories")
    parent = models.ForeignKey("self", verbose_name="상위 카테고리", null=True, blank=True, on_delete=models.CASCADE,
                               related_name="children")
    name = models.CharField("카테고리", max_length=60)
    note = models.TextField("메모", blank=True, help_text="메뉴에 보이는 이름이 다르거나, 숨김·글 수 같은 것")
    order = models.PositiveIntegerField("순서", default=0)

    class Meta:
        ordering = ["order", "pk"]

    def __str__(self):
        return f"{self.parent.name} › {self.name}" if self.parent_id else self.name

    @property
    def sel(self):
        return f"k{self.pk}"


class Placement(TrashableModel):
    """매핑: 포스트 관리까지 간 글 하나를 사이트 카테고리 하나에 넣은 것. 상태는 그 사이트에서의 진행.

    네이버 사이트에는 네이버 글쓰기 글, 그 밖의 사이트(티스토리·블로거·워드프레스)에는 티스토리 글쓰기 글을 넣는다.
    """

    class Status(models.TextChoices):
        UNSAVED = "unsaved", "미저장"
        DRAFT = "draft", "임시저장"
        PUBLISHED = "published", "발행"

    site_category = models.ForeignKey(SiteCategory, verbose_name="사이트 카테고리", on_delete=models.CASCADE,
                                      related_name="placements")
    tistory_post = models.ForeignKey("writing.Post", verbose_name="티스토리 글", null=True, blank=True,
                                     on_delete=models.CASCADE, related_name="placements")
    naver_post = models.ForeignKey("naver_writing.Post", verbose_name="네이버 글", null=True, blank=True,
                                   on_delete=models.CASCADE, related_name="placements")
    class Convert(models.TextChoices):
        """사이트별 템플릿으로 그 사이트에 맞게 바꾼 원고의 진행 (사이트별 템플릿 화면)"""
        NONE = "none", "미변환"
        REQUESTED = "requested", "변환 요청"
        DONE = "done", "변환 완료"
        CHECKED = "checked", "확인 완료"

    status = models.CharField("상태", max_length=10, choices=Status.choices, default=Status.UNSAVED)
    convert_status = models.CharField("변환", max_length=10, choices=Convert.choices, default=Convert.NONE)
    convert_note = models.CharField("변환 요청 메모", max_length=300, blank=True,
                                    help_text="이 글만 다르게 할 것 (예: 첫 문단을 더 짧게)")
    converted_title = models.CharField("변환 제목", max_length=200, blank=True)
    converted_body = models.TextField("변환 본문", blank=True, help_text="그 사이트 에디터에 붙여넣을 원고 (마크다운 또는 HTML)")
    converted_tags = models.CharField("변환 태그", max_length=500, blank=True, help_text="그 사이트 태그·라벨 칸에 넣을 것")
    converted_at = models.DateTimeField("변환한 때", null=True, blank=True)
    created_at = models.DateTimeField("넣은 날", auto_now_add=True)
    updated_at = models.DateTimeField("수정일", auto_now=True)

    class Meta:
        ordering = ["created_at", "pk"]

    def __str__(self):
        return f"{self.site_category} ← {self.post}"

    @property
    def post(self):
        return self.tistory_post or self.naver_post

    @property
    def writer(self):
        return "naver" if self.naver_post_id else "tistory"

    @property
    def title(self):
        """휴지통 목록에 보이는 이름"""
        post = self.post
        return f"{post.title if post else '글'} → {self.site_category.blog.name} › {self.site_category}"


class ClassChange(models.Model):
    """AI 가 저장소에 남긴 분류 변경 파일(일일루틴/분류변경/*.json) 한 개를 DB 에 반영한 기록. 같은 파일은 한 번만."""

    name = models.CharField("파일", max_length=120, unique=True)
    applied_at = models.DateTimeField("반영한 때", auto_now_add=True)
    ok = models.BooleanField("모두 반영", default=True)
    log = models.TextField("결과", blank=True)

    class Meta:
        ordering = ["-applied_at", "-pk"]
        verbose_name = "분류 변경 기록"
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name
