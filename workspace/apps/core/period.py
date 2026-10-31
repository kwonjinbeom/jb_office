"""운영·일일루틴 위쪽 달력 띠: 일별(한 주 띠)·월별(한 해 띠).

?date=YYYY-MM-DD → 일별, ?month=YYYY-MM → 월별. 띠의 칸마다 완료/미완료 상태를 단다.
템플릿은 includes/period_bar.html.
"""
import calendar
from datetime import date, timedelta

WEEKDAYS = "월화수목금토일"


def month_end(first: date) -> date:
    return first.replace(day=calendar.monthrange(first.year, first.month)[1])


def add_months(first: date, n: int) -> date:
    m = first.year * 12 + first.month - 1 + n
    return date(m // 12, m % 12 + 1, 1)


def parse(request, today: date) -> tuple[str, date]:
    try:
        y, m = (int(x) for x in request.GET.get("month", "").split("-"))
        return "month", date(y, m, 1)
    except ValueError:
        pass
    try:
        return "day", date.fromisoformat(request.GET.get("date", ""))
    except ValueError:
        return "day", today


def bounds(mode: str, sel: date) -> tuple[date, date]:
    """지금 보는 기간 (하루 또는 한 달)."""
    return (sel, sel) if mode == "day" else (sel, month_end(sel))


def strip_bounds(mode: str, sel: date) -> tuple[date, date]:
    """띠 전체 기간 (그 주 월~일 또는 그 해 1~12월)."""
    if mode == "day":
        monday = sel - timedelta(days=sel.weekday())
        return monday, monday + timedelta(days=6)
    return date(sel.year, 1, 1), date(sel.year, 12, 31)


def days_between(lo: date, hi: date):
    return [lo + timedelta(days=i) for i in range((hi - lo).days + 1)]


def bar(mode: str, sel: date, today: date, state, ahead=None) -> dict:
    """state(lo, hi) → "done" | "todo" | "" (목표 없음). 오늘 뒤의 칸은 상태를 달지 않는다.
    ahead(d) 를 주면 오늘 뒤의 날 칸에도 그 값을 단다 — 미리 쓴 날만 '완료' (일별, 2026-10-31 사용자)."""
    lo, _ = strip_bounds(mode, sel)
    cells = []
    if mode == "day":
        for i in range(7):
            d = lo + timedelta(days=i)
            cells.append({"href": f"?date={d}", "top": WEEKDAYS[i], "main": d.day, "title": str(d),
                          "on": d == sel, "today": d == today, "weekend": i >= 5,
                          "state": state(d, d) if d <= today else (ahead(d) if ahead else "")})
        nav = {"prev": f"?date={sel - timedelta(days=1)}", "next": f"?date={sel + timedelta(days=1)}",
               "strip_prev": f"?date={sel - timedelta(days=7)}", "strip_next": f"?date={sel + timedelta(days=7)}",
               "prev_label": "전날", "next_label": "다음 날", "strip_prev_label": "지난주", "strip_next_label": "다음 주"}
    else:
        for m in range(1, 13):
            first = date(sel.year, m, 1)
            cells.append({"href": f"?month={first:%Y-%m}", "top": f"{first:%y}년", "main": f"{m}월", "title": f"{first:%Y-%m}",
                          "on": m == sel.month, "today": (first.year, first.month) == (today.year, today.month),
                          "weekend": False, "state": state(first, min(month_end(first), today)) if first <= today else ""})
        nav = {"prev": f"?month={add_months(sel, -1):%Y-%m}", "next": f"?month={add_months(sel, 1):%Y-%m}",
               "strip_prev": f"?month={add_months(sel, -12):%Y-%m}", "strip_next": f"?month={add_months(sel, 12):%Y-%m}",
               "prev_label": "지난달", "next_label": "다음 달", "strip_prev_label": "지난해", "strip_next_label": "다음 해"}
    is_now = sel == today if mode == "day" else (sel.year, sel.month) == (today.year, today.month)
    return {"mode": mode, "sel": sel, "weekday": WEEKDAYS[sel.weekday()], "is_now": is_now,
            "cells": cells, "nav": nav, "month_value": f"{sel:%Y-%m}"}
