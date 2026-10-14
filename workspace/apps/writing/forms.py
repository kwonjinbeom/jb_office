import json
from datetime import date

from django import forms
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError

from apps.content.forms import style_form, FolderChoice, folder_choices
from apps.content.models import Content, Folder
from .catalog import MANUAL_CHECKS, TEMPLATES
from .models import Draft, WritingProfile, WritingTemplate


def template_choices():
    return [(t["key"], t["name"]) for t in TEMPLATES] + [
        (f"custom:{t.pk}", f"내 템플릿 · {t.name}")
        for t in WritingTemplate.objects.all()
    ]


class NewDraftForm(forms.Form):
    title = forms.CharField(label="글 제목·소재", max_length=160)
    template_key = forms.ChoiceField(label="글 형식")
    profile = forms.ModelChoiceField(
        label="작성 규칙",
        queryset=WritingProfile.objects.all(),
        required=False,
        empty_label="기본 규칙",
    )
    folder = FolderChoice(label="폴더", queryset=Folder.objects.none(), required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["template_key"].choices = template_choices()
        folder_choices(self.fields["folder"], "blog")
        style_form(self)


class DraftForm(forms.ModelForm):
    template_key = forms.ChoiceField(label="글 형식")
    title = forms.CharField(label="제목", max_length=160)
    body = forms.CharField(
        label="본문",
        required=False,
        max_length=120000,
        strip=False,
        widget=forms.Textarea(attrs={"rows": 24, "spellcheck": "false"}),
    )
    status = forms.ChoiceField(
        label="작성 상태",
        choices=[
            (v, label)
            for v, label in Content.Status.choices
            if v in ["draft", "review", "ready", "published", "hold"]
        ],
    )
    folder = FolderChoice(label="폴더", queryset=Folder.objects.none(), required=False)
    sources = forms.CharField(required=False, widget=forms.HiddenInput)
    checks = forms.MultipleChoiceField(
        label="최종 확인",
        choices=MANUAL_CHECKS,
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )
    revision = forms.IntegerField(widget=forms.HiddenInput)
    signature = forms.CharField(widget=forms.HiddenInput)

    class Meta:
        model = Draft
        fields = [
            "profile",
            "template_key",
            "keyword",
            "tags",
            "question",
            "answer",
            "experience",
            "description",
            "commercial",
            "published_url",
            "published_on",
        ]
        widgets = {
            "question": forms.Textarea(attrs={"rows": 3}),
            "experience": forms.Textarea(attrs={"rows": 5}),
            "published_on": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["template_key"].choices = template_choices()
        if self.instance.template_key not in dict(self.fields["template_key"].choices):
            self.fields["template_key"].choices.append(
                (self.instance.template_key, "삭제된 템플릿 · 기본 틀 사용")
            )
        folder_choices(self.fields["folder"], "blog")
        for name in ["question", "experience"]:
            self.fields[name].max_length = 12000
            self.fields[name].widget.attrs["maxlength"] = 12000
        style_form(self)

    def clean_sources(self):
        try:
            sources = json.loads(self.cleaned_data["sources"] or "[]")
        except (ValueError, TypeError):
            raise ValidationError("자료 목록을 확인하세요.")
        if not isinstance(sources, list) or len(sources) > 30:
            raise ValidationError("자료는 최대 30개까지 저장할 수 있습니다.")
        cleaned = []
        for source in sources:
            if not isinstance(source, dict):
                raise ValidationError("자료 형식을 확인하세요.")
            row = {}
            for key, maximum in [
                ("title", 180),
                ("url", 600),
                ("note", 2000),
                ("checked_on", 10),
            ]:
                value = source.get(key, "")
                if not isinstance(value, str) or len(value) > maximum:
                    raise ValidationError("자료의 제목·주소·메모 길이를 확인하세요.")
                row[key] = value.strip()
            if row["url"]:
                URLValidator(schemes=["http", "https"])(row["url"])
            if row["checked_on"]:
                try:
                    date.fromisoformat(row["checked_on"])
                except ValueError:
                    raise ValidationError("자료 확인일을 확인하세요.")
            row["verified"] = source.get("verified") is True
            if any(row[k] for k in ["title", "url", "note"]):
                cleaned.append(row)
        return cleaned

    def clean_tags(self):
        tags = list(
            dict.fromkeys(
                t.strip().lstrip("#")
                for t in self.cleaned_data["tags"].split(",")
                if t.strip().lstrip("#")
            )
        )
        if len(tags) > 10 or any(len(tag) > 30 for tag in tags):
            raise ValidationError("태그는 30자 이내로 최대 10개까지 적으세요.")
        return ", ".join(tags)

    def clean(self):
        values = super().clean()
        for name in ["body", "question", "experience"]:
            if name in values:
                values[name] = values[name].replace("\r\n", "\n").replace("\r", "\n")
        return values


class ProfileForm(forms.ModelForm):
    class Meta:
        model = WritingProfile
        fields = [
            "name",
            "blog_url",
            "audience",
            "tone",
            "rules",
            "closing",
            "disclosure",
            "target_length",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["rules"].max_length = 12000
        style_form(self)


class TemplateForm(forms.ModelForm):
    class Meta:
        model = WritingTemplate
        fields = ["name", "description", "body"]
        widgets = {"body": forms.Textarea(attrs={"rows": 20})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["body"].max_length = 30000
        style_form(self)


class AISettingsForm(forms.Form):
    api_key = forms.CharField(
        label="OpenAI API 키",
        required=False,
        max_length=500,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        help_text="변경할 때만 입력하세요. 저장한 키는 다시 표시하지 않습니다.",
    )
    model = forms.RegexField(
        label="모델",
        regex=r"^[a-zA-Z0-9._:/-]{1,100}$",
        initial="gpt-4.1-mini",
        help_text="기본값: gpt-4.1-mini. API 계정에서 사용 가능한 모델을 입력하세요.",
    )
    remove_key = forms.BooleanField(label="저장된 API 키 삭제", required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        style_form(self)


class BackupForm(forms.Form):
    file = forms.FileField(
        label="원고 백업 JSON",
        help_text="이 도우미에서 내려받은 백업을 새 원고로 불러옵니다. 게시 상태와 게시 URL은 초기화됩니다.",
    )

    def clean_file(self):
        file = self.cleaned_data["file"]
        if file.size > 512000:
            raise ValidationError("백업 파일은 500KB 이내로 올려 주세요.")
        try:
            data = json.loads(file.read().decode("utf-8-sig"))
        except (ValueError, UnicodeDecodeError):
            raise ValidationError("JSON 원고 백업을 읽지 못했습니다.")
        if (
            not isinstance(data, dict)
            or not isinstance(data.get("content"), dict)
            or not isinstance(data.get("draft"), dict)
        ):
            raise ValidationError("이 도우미의 원고 백업 형식이 아닙니다.")
        for key in ["title", "body"]:
            if not isinstance(data["content"].get(key), str):
                raise ValidationError("백업의 제목·본문을 확인하세요.")
        return data
