from django import forms

from .models import Memo


class MemoForm(forms.ModelForm):
    class Meta:
        model = Memo
        fields = ["title", "body", "pinned", "tags"]
        widgets = {"body": forms.Textarea(attrs={"rows": 14})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.label_suffix = ""
        for name, field in self.fields.items():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.setdefault("class", "checkbox")
            else:
                field.widget.attrs.setdefault("class", "input")
        self.fields["title"].widget.attrs.setdefault("autofocus", "autofocus")
