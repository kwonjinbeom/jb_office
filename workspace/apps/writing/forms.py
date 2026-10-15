from django import forms

from .models import Post

# 화면마다 고칠 수 있는 상태 칸. 임시 템플릿에는 상태가 없다.
STAGE_FIELDS = {
    Post.Stage.TEMP: [],
    Post.Stage.REVIEW: ["review_status"],
    Post.Stage.POST: ["write_status", "publish_status", "published_url", "published_on"],
}


class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = [
            "title", "summary", "body",
            "review_status", "write_status", "publish_status", "published_url", "published_on",
        ]
        widgets = {
            "title": forms.TextInput(attrs={"class": "input", "autofocus": True}),
            "summary": forms.TextInput(attrs={"class": "input"}),
            "body": forms.Textarea(attrs={"class": "input", "rows": 18, "data-autogrow": ""}),
            "review_status": forms.Select(attrs={"class": "input"}),
            "write_status": forms.Select(attrs={"class": "input"}),
            "publish_status": forms.Select(attrs={"class": "input"}),
            "published_url": forms.URLInput(attrs={"class": "input", "placeholder": "https://"}),
            "published_on": forms.DateInput(attrs={"class": "input", "type": "date"}, format="%Y-%m-%d"),
        }

    def __init__(self, *args, stage=Post.Stage.TEMP, **kwargs):
        super().__init__(*args, **kwargs)
        self.label_suffix = ""
        keep = {"title", "summary", "body", *STAGE_FIELDS[stage]}
        for name in list(self.fields):
            if name not in keep:
                del self.fields[name]
