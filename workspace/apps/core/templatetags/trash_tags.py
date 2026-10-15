from django import template
from django.utils.html import format_html

register = template.Library()


@register.simple_tag
def trash_attrs(obj, label=None):
    if obj is None:
        return ""
    from apps.core.trash import title_for
    return format_html('data-trash-model="{}" data-trash-id="{}" data-trash-title="{}"', obj._meta.label_lower, obj.pk, title_for(obj))
