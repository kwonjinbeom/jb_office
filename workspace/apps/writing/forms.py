from django import forms

from apps.blog_types import classify

from .models import Post
from .render import clean_html, is_html

# 화면마다 고칠 수 있는 상태 칸. 임시글에는 상태가 없다.
STAGE_FIELDS = {
    Post.Stage.TEMP: [],
    Post.Stage.REVIEW: ["review_status"],
    Post.Stage.POST: ["write_status", "publish_status", "published_url", "published_on"],
}


class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = [
            "title", "summary", "tags", "body", "target",
            "review_status", "write_status", "publish_status", "published_url", "published_on",
        ]
        widgets = {
            "title": forms.Textarea(attrs={"class": "wr-title-input", "rows": 1, "placeholder": "제목을 입력하세요",
                                           "maxlength": 200}),  # 높이는 editor.js 가 맞춘다
            "summary": forms.TextInput(attrs={"class": "input", "placeholder": "목록과 검색 설명에 쓰는 한두 줄"}),
            "tags": forms.TextInput(attrs={"class": "wr-tag-input", "placeholder": "#태그입력 (쉼표로 구분)"}),
            "body": forms.Textarea(attrs={"hidden": True}),  # 편집기(contenteditable) 내용을 저장 직전에 옮겨 담는다
            "review_status": forms.Select(attrs={"class": "input"}),
            "write_status": forms.Select(attrs={"class": "input"}),
            "publish_status": forms.Select(attrs={"class": "input"}),
            "published_url": forms.URLInput(attrs={"class": "input", "placeholder": "https://"}),
            "published_on": forms.DateInput(attrs={"class": "input", "type": "date"}, format="%Y-%m-%d"),
        }

    def __init__(self, *args, stage=Post.Stage.TEMP, **kwargs):
        super().__init__(*args, **kwargs)
        self.label_suffix = ""
        keep = {"title", "summary", "tags", "body", "target", *STAGE_FIELDS[stage]}
        for name in list(self.fields):
            if name not in keep:
                del self.fields[name]
        # 글 관리의 글 분류. 모든 화면(임시 → 검토 → 포스트)에서 고친다.
        self.fields["classification"] = forms.ChoiceField(
            label="분류", required=False, choices=classify.choices("tistory"),
            initial=classify.value_of(self.instance) if self.instance.pk else "",
            widget=forms.Select(attrs={"class": "input"}))
        # 타겟: 운영 화면의 블로그 이름 중에서 고른다. 목록에 없는 예전 값도 그대로 남긴다.
        from apps.blog_rules.models import Blog
        names = list(Blog.objects.values_list("name", flat=True))
        current = self.instance.target if self.instance.pk else ""
        self.fields["target"] = forms.ChoiceField(
            label="타겟", required=False,
            choices=[("", "정하지 않음")] + [(n, n) for n in names] + ([(current, current)] if current and current not in names else []),
            widget=forms.Select(attrs={"class": "input"}))

    def save(self, commit=True):
        classify.assign(self.instance, self.cleaned_data.get("classification"))
        return super().save(commit=commit)

    def clean_title(self):
        return " ".join(self.cleaned_data["title"].split())

    def clean_body(self):
        """편집기에서 온 HTML 은 허용한 태그·속성만 남긴다. 마크다운은 그대로 둔다 (글 보기에서 변환)."""
        body = (self.cleaned_data.get("body") or "").strip()
        return clean_html(body) if is_html(body) else body
