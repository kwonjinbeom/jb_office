from django import forms

from .models import Task


class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ["title", "idea", "stage", "due", "notes", "done"]
        widgets = {
            "due": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "notes": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.label_suffix = ""
        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.setdefault("class", "checkbox")
            elif isinstance(field.widget, forms.Select):
                field.widget.attrs.setdefault("class", "select")
            else:
                field.widget.attrs.setdefault("class", "input")
        self.fields["title"].widget.attrs.setdefault("autofocus", "autofocus")


class QuickTaskForm(forms.Form):
    """목록 상단의 한 줄 입력."""

    title = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={"class": "input", "placeholder": "할 일 입력 후 Enter"}),
    )
    due = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date", "class": "input"}))
