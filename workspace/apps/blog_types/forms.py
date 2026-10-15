from django import forms

from .models import Category, PostType, SubType


class _Styled(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.label_suffix = ""
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "input")


class CategoryForm(_Styled):
    class Meta:
        model = Category
        fields = ["code", "name", "platform", "direction", "question", "note"]
        widgets = {"note": forms.Textarea(attrs={"rows": 5})}


class PostTypeForm(_Styled):
    class Meta:
        model = PostType
        fields = ["name", "skeleton", "examples", "note"]
        widgets = {
            "examples": forms.Textarea(attrs={"rows": 3}),
            "note": forms.Textarea(attrs={"rows": 5}),
        }


class SubTypeForm(_Styled):
    class Meta:
        model = SubType
        fields = ["name", "note"]
        widgets = {"note": forms.Textarea(attrs={"rows": 8})}


FORMS = {"category": CategoryForm, "type": PostTypeForm, "sub": SubTypeForm}
