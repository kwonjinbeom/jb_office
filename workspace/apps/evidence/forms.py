from django import forms

from .models import Evidence


class EvidenceForm(forms.ModelForm):
    class Meta:
        model = Evidence
        fields = ["url", "title", "kind", "note", "idea", "stage"]
        widgets = {
            "url": forms.URLInput(attrs={"placeholder": "https://", "autofocus": "autofocus", "inputmode": "url"}),
            "note": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.label_suffix = ""
        for field in self.fields.values():
            css = "select" if isinstance(field.widget, forms.Select) else "input"
            field.widget.attrs.setdefault("class", css)
