from django import forms

from .models import Blog, Rule


class _Styled(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.label_suffix = ""
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "input")


class BlogForm(_Styled):
    class Meta:
        model = Blog
        fields = ["name", "platform", "status", "address", "account", "revenue", "daily", "daily_note",
                  "content", "kpi", "note"]
        widgets = {"note": forms.Textarea(attrs={"rows": 4}), "daily": forms.NumberInput(attrs={"min": 0, "max": 5})}


class RuleForm(_Styled):
    class Meta:
        model = Rule
        fields = ["blog", "body", "note"]
