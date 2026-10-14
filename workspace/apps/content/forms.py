from django import forms

from .models import Content, Folder, Publication
from .tree import decorate_tree, subtree_ids


def style_form(form):
    form.label_suffix = ""
    for field in form.fields.values():
        field.widget.attrs.setdefault("class", "select" if isinstance(field.widget, forms.Select) else "input")
        if isinstance(field.widget, forms.Textarea):
            field.widget.attrs.setdefault("rows", 5)


class FolderChoice(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return self.paths.get(obj.pk, obj.name)


def folder_choices(field, workspace, excluded=None):
    nodes = decorate_tree(Folder.objects.filter(workspace=workspace))
    field.paths = {node.pk: node.path for node in nodes}
    field.queryset = Folder.objects.filter(workspace=workspace).exclude(pk__in=excluded or [])
    field.choices = [("", "최상위" if field.label == "상위 폴더" else "미분류")] + [(node.pk, node.path) for node in nodes if node.pk not in (excluded or [])]


class FolderForm(forms.ModelForm):
    parent = FolderChoice(label="상위 폴더", queryset=Folder.objects.none(), required=False)

    class Meta:
        model = Folder
        fields = ["name", "parent", "audience", "purpose", "tone", "rules"]

    def __init__(self, *args, workspace, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.workspace = workspace
        nodes = decorate_tree(Folder.objects.filter(workspace=workspace))
        folder_choices(self.fields["parent"], workspace, subtree_ids(nodes, self.instance.pk))
        style_form(self)


class ContentForm(forms.ModelForm):
    folder = FolderChoice(label="폴더", queryset=Folder.objects.none(), required=False)

    class Meta:
        model = Content
        fields = ["title", "folder", "kind", "status", "summary", "outline", "body", "scenes", "idea"]
        widgets = {"body": forms.Textarea(attrs={"rows": 16})}

    def __init__(self, *args, workspace, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.workspace = workspace
        folder_choices(self.fields["folder"], workspace)
        if workspace == "blog":
            self.fields["body"].label = "본문·글 템플릿"
            self.fields["scenes"].label = "자료·출처"
        else:
            self.fields["body"].label = "대본·대본 템플릿"
        style_form(self)


class PublicationForm(forms.ModelForm):
    class Meta:
        model = Publication
        fields = ["channel", "title", "version", "url", "published_on", "result"]
        widgets = {"published_on": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        style_form(self)
