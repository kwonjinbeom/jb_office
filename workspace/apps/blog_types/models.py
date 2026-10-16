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
