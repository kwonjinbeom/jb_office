"""블로그·카페 › 사이트별 템플릿 (2026-10-16 사용자).

사이트(운영 화면의 블로그)마다 컨셉에 맞는 말투·구성 템플릿이 있고, 플랫폼(티스토리·네이버·워드프레스·블로거)마다 붙여넣기 포맷이 조금씩
다르다. 글 매핑 관리에서 사이트 카테고리에 넣은 글(Placement)을 이 두 가지에 맞게 바꾼 원고가 Placement.converted_* 에 저장된다.
변환은 사용자가 Claude 에게 요청한다: 이 화면의 '요청문'(prompt.py)을 Claude 가 읽고 변환본을 채운다.
"""
from django.db import models

from apps.blog_rules.models import Blog


class PlatformFormat(models.Model):
    platform = models.CharField("플랫폼", max_length=12, choices=Blog.Platform.choices, unique=True)
    guide = models.TextField("붙여넣기 포맷", blank=True, help_text="그 에디터에 붙일 때 지킬 것 (소제목·표·이미지·링크·태그 등)")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["pk"]

    def __str__(self):
        return self.get_platform_display()


class SiteTemplate(models.Model):
    blog = models.OneToOneField(Blog, verbose_name="사이트", on_delete=models.CASCADE, related_name="template")
    tone = models.TextField("말투·멘트", blank=True, help_text="예: 정보성은 해요체·판단 한 줄, 일상은 1인칭 짧은 문장·감정 한 줄")
    structure = models.TextField("구성", blank=True, help_text="도입 → 본문 → 마무리를 어떤 모양으로 (소제목 수, 표, 요약 상자 등)")
    rules = models.TextField("꼭 지킬 것", blank=True, help_text="이 사이트에서만 지킬 것 (금지어, 표시 문구, 링크 위치 등)")
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.blog} 템플릿"
