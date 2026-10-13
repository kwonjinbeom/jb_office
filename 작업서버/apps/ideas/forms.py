from django import forms

from .models import Idea


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
        for field in self.fields.values():
            css = "select" if isinstance(field.widget, forms.Select) else "input"
            field.widget.attrs.setdefault("class", css)
