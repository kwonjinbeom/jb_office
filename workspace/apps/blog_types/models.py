"""수익형(찍어내기) 계정의 글 분류: 카테고리 › 타입 › 하위.

카테고리 = 사게 만드는 방향 (A 문제 해결 ~ G 여행·체험). 나누는 기준은 '글을 연 사람의 질문'이다.
타입 = 그 방향 안에서 매번 같은 틀로 물건만 바꿔 쓰는 글 모양.
하위 = 타입을 실제로 나눠 쓰는 단위 (품목군·대상·변형 등).
처음 값과 짠 이유: 콘텐츠/블로그_카페/포스팅자동화/08_수익형_카테고리.md
"""
from django.db import models


class Category(models.Model):
    class Platform(models.TextChoices):
        ALL = "all", "공통"
        NAVER = "naver", "네이버"
        TISTORY = "tistory", "티스토리"

    code = models.CharField("기호", max_length=4, help_text="A, B, C …")
    name = models.CharField("카테고리", max_length=40)
    direction = models.CharField("사게 만드는 방향", max_length=120, blank=True, help_text="예: 불편 → 해결템")
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


class PostType(models.Model):
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


class SubType(models.Model):
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
