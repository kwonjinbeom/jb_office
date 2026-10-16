from django.db import models
from apps.core.models import TrashableModel
from django.urls import reverse


class Post(TrashableModel):
    """네이버 글 한 편. 임시 템플릿 → 검토 템플릿 → 포스트 관리 세 화면을 오간다.

    화면(stage)마다 그 화면에서 하는 일의 상태가 따로 있다.
    다른 화면으로 옮겨도 상태값은 지우지 않는다 (되돌아오면 하던 데서 이어간다).
    """

    class Stage(models.TextChoices):
        TEMP = "temp", "임시 템플릿"
        REVIEW = "review", "검토 템플릿"
        POST = "post", "포스트 관리"

    class Review(models.TextChoices):
        TODO = "todo", "미검토"
        DOING = "doing", "검토 중"
        DONE = "done", "검토 완료"

    class Write(models.TextChoices):
        TODO = "todo", "미작성"
        DOING = "doing", "작성 중"
        DONE = "done", "작성 완료"

    class Publish(models.TextChoices):
        TODO = "todo", "미발행"
        DONE = "done", "발행 완료"

    stage = models.CharField("화면", max_length=10, choices=Stage.choices, default=Stage.TEMP)
    title = models.CharField("제목", max_length=200)
    summary = models.CharField("내용 요약", max_length=300, blank=True, help_text="목록에 보이는 한두 줄")
    body = models.TextField("내용", blank=True)
    tags = models.CharField("태그", max_length=300, blank=True, help_text="쉼표로 구분 (예: 단풍절정, 가을여행)")
    review_status = models.CharField("검토", max_length=10, choices=Review.choices, default=Review.TODO)
    write_status = models.CharField("작성", max_length=10, choices=Write.choices, default=Write.TODO)
    publish_status = models.CharField("발행", max_length=10, choices=Publish.choices, default=Publish.TODO)
    published_url = models.URLField("발행 주소", max_length=500, blank=True)
    published_on = models.DateField("발행일", null=True, blank=True)
    # 글 관리의 글 분류 (대분류 › 카테고리 › 타입 › 하위). 가장 깊게 고른 단계까지 채운다. apps/blog_types/classify.py
    bt_category = models.ForeignKey("blog_types.Category", verbose_name="분류 카테고리", null=True, blank=True,
                                    on_delete=models.SET_NULL, related_name="%(app_label)s_posts")
    bt_type = models.ForeignKey("blog_types.PostType", verbose_name="분류 타입", null=True, blank=True,
                                on_delete=models.SET_NULL, related_name="%(app_label)s_posts")
    bt_sub = models.ForeignKey("blog_types.SubType", verbose_name="분류 하위", null=True, blank=True,
                               on_delete=models.SET_NULL, related_name="%(app_label)s_posts")
    created_at = models.DateTimeField("만든 날", auto_now_add=True)
    updated_at = models.DateTimeField("수정일", auto_now=True)

    class Meta:
        ordering = ["-updated_at", "-pk"]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("naver_writing:detail", args=[self.pk])

    @property
    def tag_list(self):
        """쉼표·줄바꿈으로 나눈 태그. 앞의 # 은 떼어 낸다."""
        parts = (t.strip().lstrip("#").strip() for t in self.tags.replace("\n", ",").split(","))
        return [t for t in parts if t]

    @property
    def excerpt(self):
        from .render import plain_text, render_body
        return self.summary or " ".join(plain_text(render_body(self.body), drop_slots=True).split())[:140]

    @property
    def is_published(self):
        return self.publish_status == self.Publish.DONE

    # 화면 사이 이동: 임시 ↔ 검토 ↔ 포스트. 한 번에 한 칸씩만 옮긴다.
    def next_stage(self):
        return {self.Stage.TEMP: self.Stage.REVIEW, self.Stage.REVIEW: self.Stage.POST}.get(self.stage)

    def prev_stage(self):
        if self.is_published:  # 발행한 글은 포스트 관리에 남긴다
            return None
        return {self.Stage.REVIEW: self.Stage.TEMP, self.Stage.POST: self.Stage.REVIEW}.get(self.stage)

    def can_move_to(self, stage):
        return stage is not None and stage in (self.next_stage(), self.prev_stage())
