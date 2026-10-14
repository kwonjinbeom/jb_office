from django import forms

from .models import SearchStandard
from .standard import FIELDS, FOCUS_EXAMPLE, SECTIONS


class StandardForm(forms.ModelForm):
    class Meta:
        model = SearchStandard
        fields = [*FIELDS, "note"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.label_suffix = ""
        for name, _, guide, _ in SECTIONS:
            field = self.fields[name]
            field.help_text = guide
            # 높이는 내용 길이에 맞춰 자란다 (static/js/app.js 의 data-autogrow).
            field.widget = forms.Textarea(attrs={"class": "input", "rows": 4, "spellcheck": "false", "data-autogrow": ""})
        self.fields["focus"].widget.attrs.update(rows=3, placeholder=FOCUS_EXAMPLE)
        self.fields["note"].widget.attrs.update({"class": "input", "placeholder": "예: 도구 비중을 늘리고 출처를 2개 이상으로"})
