"""memorily 연재 (2026-10-20 사용자): AI(Claude·Codex)와 블로그 자동화를 만든 과정을 회차로 나눠 쓴다.

보여줄 것 (사용자): 맨 처음 화면부터 필요한 화면을 하나씩 더하고, 써 보며 기능을 바꾸고, 프롬프트를 다듬고, 부족한 점을 메워
점점 체계가 잡혀 가는 모습. 회차 하나 = 화면(또는 기능) 하나가 생기고 바뀐 흐름. 근거는 커밋·문서.
'글로 만들기'를 누르면 memorily 임시글이 생긴다: 필요했던 것 → 처음 만든 것 → 써 보니 부족했던 점 → 이렇게 바꿨다 → 지금 모습.
"""
from django.db import models

# 흐름 줄의 말머리. 글 뼈대에서 '처음' 은 처음 만든 것, '부족' 은 부족했던 점, 나머지는 바꾼 것, '지금' 은 지금 모습으로 간다
STEP_WORDS = ("처음", "부족", "바꿈", "메움", "나눔", "합침", "넓힘", "정리", "고침", "다듬음", "지금")


class Episode(models.Model):
    class Status(models.TextChoices):
        # 값은 공통 상태 버튼 색(todo·doing·done)을 그대로 쓰려고 맞췄다
        PLAN = "todo", "계획"
        WRITING = "doing", "쓰는 중"
        DONE = "done", "발행"

    number = models.PositiveIntegerField("회차", unique=True)
    title = models.CharField("제목", max_length=200)
    screen = models.CharField("화면", max_length=80, blank=True, help_text="이 회차에서 생기거나 바뀐 화면 (예: 글 관리 · 글 보기)")
    hook = models.CharField("필요했던 것", max_length=300, blank=True, help_text="왜 이 화면이 필요했나 한 문장")
    period = models.CharField("기간", max_length=40, blank=True, help_text="예: 10-13 ~ 10-15")
    points = models.TextField("흐름", blank=True,
                              help_text="한 줄에 하나, 앞에 '처음:' · '부족:' · '바꿈:' · '메움:' · '지금:' 같은 말을 붙인다")
    sources = models.TextField("근거", blank=True, help_text="커밋·문서·PR, 한 줄에 하나")
    note = models.TextField("내 추가 설명", blank=True, help_text="글쓰기 때 '필요했던 것' 아래에 내 말로 들어간다")
    status = models.CharField("상태", max_length=10, choices=Status.choices, default=Status.PLAN)
    post = models.ForeignKey("writing.Post", verbose_name="글", null=True, blank=True, on_delete=models.SET_NULL,
                             related_name="episodes")
    updated_at = models.DateTimeField("수정일", auto_now=True)

    class Meta:
        ordering = ["number"]
        verbose_name = "연재 회차"
        verbose_name_plural = "연재 회차"

    def __str__(self):
        return f"EP.{self.number} {self.title}"

    @property
    def point_list(self):
        return [line.strip(" -·") for line in self.points.splitlines() if line.strip(" -·")]

    @property
    def steps(self):
        """흐름 줄을 (말머리, 내용)으로: '바꿈 (10-16): …' → ('바꿈', '(10-16) …'). 말머리가 없으면 ('', 줄)."""
        out = []
        for line in self.point_list:
            head, sep, rest = line.partition(":")
            word = head.split("(")[0].strip()
            if sep and word in STEP_WORDS:
                date = head[len(word):].strip()
                out.append((word, f"{date} {rest.strip()}".strip()))
            else:
                out.append(("", line))
        return out

    @property
    def source_list(self):
        return [line.strip(" -·") for line in self.sources.splitlines() if line.strip(" -·")]
