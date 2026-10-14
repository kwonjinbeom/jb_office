from django import forms
from apps.content.forms import style_form
from apps.content.tree import decorate_tree, subtree_ids
from .models import Discussion


class DiscussionForm(forms.ModelForm):
    class Meta:
        model = Discussion
        fields = ["area", "parent", "name", "summary", "next_action", "status", "amount", "partner", "idea", "content"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        nodes = decorate_tree(Discussion.objects.all())
        excluded = subtree_ids(nodes, self.instance.pk)
        self.fields["parent"].queryset = Discussion.objects.exclude(pk__in=excluded)
        self.fields["parent"].choices = [("", "최상위")] + [(node.pk, f"{node.get_area_display()} / {node.path}") for node in nodes if node.pk not in excluded]
        self.fields["parent"].help_text = "같은 메뉴의 주제를 선택하세요. 세부 주제는 계속 나눌 수 있습니다."
        style_form(self)


class QuickForm(forms.ModelForm):
    class Meta:
        model = Discussion
        fields = ["summary", "next_action", "status"]
