"""창작콘텐츠 (2026-10-22 사용자): 상상 소재 하나를 여러 방식의 창작물로 만들어 보는 검증 화면.

메뉴: 작품 리스트 · 인스타 카툰 · 숏폼 영상 · 쓰레드 글 · AI 이미지 설정집 · 검증 기록.
작품은 apps/studio/works.py (DB 없음). 그림은 브라우저에서 static/studio/js 가 그린다.
"""
from django.http import Http404
from django.shortcuts import render

from . import works as W


# 숏폼 콘티 표에 보이는 효과음 이름 (static/studio/js/sfx.js 의 FX)
SFX_LABEL = {"pop": "뿅", "steps": "발소리", "door": "문 열림", "click": "딸깍", "blink": "깜빡", "plug": "플러그",
             "sad": "슬픈 나팔", "freeze": "얼어붙음", "ice": "툭", "beep": "삑", "micro": "전자레인지", "ding": "띵",
             "flood": "쏟아짐", "swish": "휙", "shout": "버럭", "shout2": "버럭", "rimshot": "바둠츠",
             "hum_on": "냉장고 웅웅", "hum_off": "웅웅 끝"}


def _sfx(cut):
    out = []
    for _, name in cut.get("sfx", []):
        label = SFX_LABEL.get(name, name)
        if label not in out:
            out.append(label)
    return out


def _work(request):
    key = request.GET.get("w")
    work = W.get(key) if key else W.WORKS[0]
    if work is None:
        raise Http404("없는 작품")
    return work


def _page(request, nav_key, template, title, **extra):
    request.nav_key = nav_key
    work = _work(request)
    rows, at = [], 0.0
    for i, c in enumerate(work["cuts"]):  # 한 줄 자막·시작 초 (목록·콘티 표용)
        rows.append({"i": i, "no": i + 1, "cap": c["cap"].replace("\n", " "),
                     "say": (c.get("hook") or c["cap"]).replace("\n", " "),
                     "start": round(at, 1), "end": round(at + c["dur"], 1), "cut": c, "tail": work["tail"][i], "sfx": _sfx(c)})
        at += c["dur"]
    ctx = {"page_title": title, "work": work, "works": W.WORKS, "seconds": W.total_seconds(work), "rows": rows,
           "work_js": {k: work[k] for k in ("key", "series", "title", "cuts")}}
    ctx.update(extra)
    return render(request, template, ctx)


def index(request):
    return _page(request, "studio", "studio/index.html", "창작콘텐츠 리스트")


def cartoon(request):
    return _page(request, "studio_cartoon", "studio/cartoon.html", "인스타 카툰")


def shorts(request):
    return _page(request, "studio_shorts", "studio/shorts.html", "숏폼 영상")


def thread(request):
    return _page(request, "studio_thread", "studio/thread.html", "쓰레드 글")


def prompts(request):
    return _page(request, "studio_prompts", "studio/prompts.html", "AI 이미지 설정집")


def review(request):
    return _page(request, "studio_review", "studio/review.html", "검증 기록")
