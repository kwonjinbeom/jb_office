from django import forms

from .models import Idea, IdeaLog, Stage


def _style(form: forms.BaseForm) -> None:
    form.label_suffix = ""
    for field in form.fields.values():
        if isinstance(field.widget, forms.CheckboxInput):
            field.widget.attrs.setdefault("class", "checkbox")
        elif isinstance(field.widget, forms.Select):
            field.widget.attrs.setdefault("class", "select")
        else:
            field.widget.attrs.setdefault("class", "input")


class StageForm(forms.ModelForm):
    class Meta:
        model = Stage
        fields = ["title", "goal", "status", "due", "result"]
        widgets = {
            "due": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "goal": forms.Textarea(attrs={"rows": 3}),
            "result": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _style(self)
        self.fields["title"].widget.attrs.setdefault("autofocus", "autofocus")


class QuickStageForm(forms.Form):
    title = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={"class": "input", "placeholder": "단계 제목 입력 후 Enter (예: itch.io 상위 도구 리뷰 30개 읽기)"}),
    )


class LogForm(forms.ModelForm):
    class Meta:
        model = IdeaLog
        fields = ["body", "stage"]
        widgets = {"body": forms.Textarea(attrs={"rows": 3, "placeholder": "오늘 한 일, 알게 된 것, 다음에 할 것"})}

    def __init__(self, *args, idea: Idea | None = None, **kwargs):
        super().__init__(*args, **kwargs)
        _style(self)
        if idea is not None:
            self.fields["stage"].queryset = idea.stages.all()
        self.fields["stage"].required = False
        self.fields["stage"].empty_label = "단계 없음"


class IdeaForm(forms.ModelForm):
    class Meta:
        model = Idea
        fields = [
            "code",
            "title",
            "category",
            "status",
            "priority",
            "customer",
            "pain",
            "current_alternative",
            "money_flow",
            "evidence",
            "min_product",
            "channel",
            "risk",
            "judgement",
            "notes",
            "source_doc",
            "tags",
        ]
        widgets = {
            "pain": forms.Textarea(attrs={"rows": 3}),
            "current_alternative": forms.Textarea(attrs={"rows": 2}),
            "money_flow": forms.Textarea(attrs={"rows": 2}),
            "evidence": forms.Textarea(attrs={"rows": 3}),
            "min_product": forms.Textarea(attrs={"rows": 2}),
            "channel": forms.Textarea(attrs={"rows": 2}),
            "risk": forms.Textarea(attrs={"rows": 2}),
            "judgement": forms.Textarea(attrs={"rows": 3}),
            "notes": forms.Textarea(attrs={"rows": 6}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.label_suffix = ""
        for field in self.fields.values():
            css = "select" if isinstance(field.widget, forms.Select) else "input"
            field.widget.attrs.setdefault("class", css)
