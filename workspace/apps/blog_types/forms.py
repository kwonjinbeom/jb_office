from django import forms

from .models import Category, PostType, Section, SiteCategory, SubType


class _Styled(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.label_suffix = ""
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "input")


class SectionForm(_Styled):
    class Meta:
        model = Section
        fields = ["name", "note"]
        widgets = {"note": forms.Textarea(attrs={"rows": 4})}


class CategoryForm(_Styled):
    class Meta:
        model = Category
        fields = ["code", "name", "direction", "question", "note"]  # 플랫폼 나눔은 쓰지 않는다 (사이트별 템플릿에서)
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


class SiteCategoryForm(_Styled):
    class Meta:
        model = SiteCategory
        fields = ["name", "note"]
        widgets = {"note": forms.Textarea(attrs={"rows": 4})}


FORMS = {"section": SectionForm, "category": CategoryForm, "type": PostTypeForm, "sub": SubTypeForm,
         "sitecat": SiteCategoryForm}
