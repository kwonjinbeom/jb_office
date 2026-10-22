"""일정관리 (2026-10-22 사용자): 위는 큰 월 달력(칸마다 그날 일정을 작게), 아래 왼쪽은 고른 날 일정 목록, 아래 오른쪽은 입력·수정 폼.
한 화면에서 다 한다. 주소: ?m=2026-10 (보는 달) · d=2026-10-22 (고른 날) · e=<번호> (고칠 일정)."""
import calendar
from datetime import date, timedelta

from django import forms
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import Event

WEEKDAYS = "일월화수목금토"
SHOW = 3  # 달력 한 칸에 보이는 일정 수 (넘으면 +N)


class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = ["date", "time", "title", "note"]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "time": forms.TimeInput(attrs={"type": "time"}, format="%H:%M"),
            "note": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.label_suffix = ""
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "input")
        self.fields["title"].widget.attrs["placeholder"] = "무엇을 하나요"


def _parse_day(value, default):
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        return default


def _parse_month(value, default):
    try:
        y, m = (int(v) for v in value.split("-"))
        return date(y, m, 1)
    except (AttributeError, TypeError, ValueError):
        return default.replace(day=1)


def _url(month, day, extra=""):
    return f"{reverse('schedule:index')}?m={month:%Y-%m}&d={day.isoformat()}{extra}"


def _weeks(month, today, picked):
    """보는 달의 주(일요일 시작). 칸마다 날짜·그날 일정(앞 SHOW 개)·남은 수."""
    cal = calendar.Calendar(firstweekday=6)
    days = list(cal.itermonthdates(month.year, month.month))
    by_day = {}
    for e in Event.objects.filter(date__range=(days[0], days[-1])):
        by_day.setdefault(e.date, []).append(e)
    cells = [{"day": d, "in_month": d.month == month.month, "today": d == today, "picked": d == picked,
              "events": by_day.get(d, [])[:SHOW], "more": max(0, len(by_day.get(d, [])) - SHOW),
              "url": _url(month, d)} for d in days]
    return [cells[i:i + 7] for i in range(0, len(cells), 7)]


def index(request):
    today = timezone.localdate()
    picked = _parse_day(request.GET.get("d"), today)
    month = _parse_month(request.GET.get("m"), picked)
    editing = Event.objects.filter(pk=request.GET.get("e")).first() if request.GET.get("e", "").isdigit() else None
    form = EventForm(instance=editing, initial=None if editing else {"date": picked})
    prev_m = (month - timedelta(days=1)).replace(day=1)
    next_m = (month + timedelta(days=32)).replace(day=1)
    return render(request, "schedule/index.html", {
        "page_title": "일정관리", "month": month, "today": today, "picked": picked,
        "weekdays": WEEKDAYS, "weeks": _weeks(month, today, picked),
        "day_events": Event.objects.filter(date=picked), "form": form, "editing": editing,
        "prev_url": _url(prev_m, picked), "next_url": _url(next_m, picked), "today_url": _url(today, today),
        "back": _url(month, picked),
    })


@require_POST
def save(request):
    editing = Event.objects.filter(pk=request.POST.get("pk")).first() if request.POST.get("pk", "").isdigit() else None
    form = EventForm(request.POST, instance=editing)
    if form.is_valid():
        event = form.save()
        messages.success(request, "일정을 저장했습니다." if editing else "일정을 추가했습니다.")
        return redirect(_url(event.date, event.date))
    messages.error(request, "날짜와 일정을 확인하세요.")
    return redirect(request.POST.get("next") or "schedule:index")


@require_POST
def toggle_done(request, pk):
    event = get_object_or_404(Event, pk=pk)
    event.done = not event.done
    event.save(update_fields=["done", "updated_at"])
    return redirect(request.POST.get("next") or _url(event.date, event.date))


@require_POST
def delete(request, pk):
    event = get_object_or_404(Event, pk=pk)
    event.delete()  # 휴지통으로 (7일간 복원)
    messages.success(request, "일정을 휴지통으로 옮겼습니다.")
    return redirect(_url(event.date, event.date))
