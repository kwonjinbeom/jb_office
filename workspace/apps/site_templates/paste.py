"""플랫폼별 붙여넣기: 변환본을 통째로 복사해 그 사이트 글쓰기 화면에 붙이는 방법 (2026-10-16 조사, 근거는 포스팅자동화/13 문서).

변환본은 늘 마크다운(또는 이미 만든 HTML)으로 저장하고, 복사할 때 플랫폼에 맞는 꼴로 바꾼다.
- 티스토리: 티스토리 글쓰기와 같은 HTML(표·인용은 인라인 style, 머리글은 굵은 보통 칸) → HTML 모드에 붙이고 기본모드로 돌아와 확인
  (꾸밈 없는 HTML 은 표 테두리가 빠지고 머리글 줄이 표 밖으로 빠져 2026-10-20 바꿨다)
- 네이버: 서식 그대로(인라인 style) → 본문 Ctrl+V (HTML 입력 모드가 없다)
- 블로거: 티스토리와 같은 HTML → HTML 보기에 붙이고 작성 보기로 돌아가지 않는다 (작성 보기는 HTML 을 다시 쓴다)
- 워드프레스: 마크다운 그대로 → 블록 에디터 빈 문단에 붙이면 블록으로 바뀐다 (인라인 style 은 지워진다)
"""
import markdown

PLATFORMS = {
    "tistory": {
        "where": "글쓰기 오른쪽 위 모드를 HTML 로 바꿔 본문에 붙이고, 기본모드로 돌아와 확인",
        "body": [
            {"kind": "html", "label": "본문 HTML (HTML 모드)", "msg": "본문 HTML 을 복사했습니다. 티스토리 HTML 모드에 붙여넣으세요.",
             "hint": "티스토리 글쓰기 → 모드: HTML → 붙여넣기"},
            {"kind": "rich", "label": "본문 서식 (기본모드)", "msg": "본문을 서식 그대로 복사했습니다. 티스토리 기본모드에 붙여넣으세요.",
             "hint": "HTML 모드를 쓰기 어려울 때"},
        ],
        "tags": "발행 화면의 태그 칸",
        "after": "대표 이미지는 첫 사진을 내려받아 직접 올려 지정 · 남은 사진 자리에 사진 올리기 · 링크·유튜브 주소 줄에서 Enter · 접은글·인용·구분선 모양은 버튼으로 · "
                 "코드블럭 언어 지정 · 기본/HTML 모드를 여러 번 오가지 않기",
    },
    "naver": {
        "where": "블로그 글쓰기 본문에 Ctrl+V (서식 그대로)",
        "body": [
            {"kind": "rich", "label": "본문 (서식 그대로)", "msg": "본문을 서식 그대로 복사했습니다. 네이버 블로그 본문에 붙여넣으세요.",
             "hint": "스마트에디터 ONE 본문에 Ctrl+V"},
        ],
        "tags": "발행 창의 태그 칸 (붙여넣기로는 한 태그로 붙는다 → 아래 '네이버 태그 넣기' 북마크나 태그 하나씩 복사 + Enter)",
        "after": "맨 위 결론 인용은 네이버 '따옴표' 인용구로 바뀐다 (그대로 둔다) · 소제목 줄을 '소제목'으로 다시 지정 · 찾아 넣은 사진은 그대로 옮겨진다 · 남은 사진 자리에 직접 업로드(빈 1칸 표 지우기) · 코드는 소스코드 칸에 · "
                 "지도: 정보 카드의 📍 장소 이름을 에디터 '장소' 버튼으로 검색해 그 단락 아래에 넣기 (붙여넣기로는 지도 칸이 생기지 않는다) · "
                 "스티커·링크 카드는 에디터에서 · 본문에 의도치 않은 #태그 없는지",
    },
    "blogger": {
        "where": "글쓰기 왼쪽 위 연필 → HTML 보기에 붙이고, 작성 보기로 돌아가지 말고 미리보기",
        "body": [
            {"kind": "html", "label": "본문 HTML (HTML 보기)", "msg": "본문 HTML 을 복사했습니다. 블로거 HTML 보기에 붙여넣으세요.",
             "hint": "블로거 글쓰기 → HTML 보기 → 붙여넣기"},
        ],
        "tags": "오른쪽 라벨 칸 (쉼표, 5개쯤 — 첫째가 카테고리 라벨)",
        "after": "사진 직접 업로드(첫 사진이 목록 썸네일) · 검색 설명 · 퍼머링크(영문·숫자·-) · 작성 보기로 돌아가지 않기",
    },
    "wordpress": {
        "where": "블록 에디터 빈 문단에 붙이면 제목·목록·표·인용이 블록으로 바뀐다",
        "body": [
            {"kind": "raw", "label": "본문 마크다운 (블록 에디터)", "msg": "본문 마크다운을 복사했습니다. 워드프레스 빈 문단에 붙여넣으세요.",
             "hint": "비주얼 편집기 빈 문단에 붙여넣기"},
            {"kind": "html", "label": "본문 HTML", "msg": "본문 HTML 을 복사했습니다.", "hint": "사용자 지정 HTML 블록용"},
        ],
        "tags": "태그 칸 (쉼표)",
        "after": "이미지 블록마다 미디어 라이브러리에 올리고 대표 이미지 지정 · 발췌·카테고리·슬러그(영문) · "
                 "'사용자 지정 HTML'로 남은 블록 확인",
    },
}

# 요청문 맨 끝 '돌려줄 것': 변환본의 꼴은 모든 플랫폼이 같다 (복사할 때 이 모듈이 바꾼다)
OUTPUT = """## 돌려줄 것
- 제목 한 줄 (그 플랫폼 제목 칸에 그대로)
- 본문: 마크다운. 소제목은 ## 부터 (# 은 쓰지 않는다), 표는 | 표 |, 꾸밈(글자색·크기·글꼴)은 쓰지 않는다
  사진은 `![설명](주소)` + 다음 줄 `*사진: 작가 · 출처*`. [사진]·[그림] 자리 줄은 남기지 않는다
- 태그 한 줄: 그 플랫폼 태그 칸에 그대로 붙일 꼴 (쉼표로 구분, # 없이)
- 점검 기록: 마크다운 목록, 한 줄에 하나
  - `- 고침: 원래 값 → 고친 값 · 이유 · 출처 주소`
  - `- 미정: 무엇 · 확인 못 한 이유`
  - `- 확인: 맞다고 확인한 주요 숫자·일정 · 출처 주소`
  - 고칠 것이 없었으면 `- 고칠 것 없음` 과 확인한 출처들
- 위 '붙여넣기 포맷'의 금지 사항을 지킨다"""


def for_platform(platform):
    return PLATFORMS.get(platform, PLATFORMS["tistory"])


def clean_html(text):
    """꾸밈 없는 HTML (워드프레스 '사용자 지정 HTML'용): 이미 HTML 이면 그대로, 마크다운이면 변환만."""
    text = (text or "").strip()
    if not text:
        return ""
    if text.startswith("<"):
        return text
    return markdown.markdown(text, extensions=["tables", "sane_lists"])


# 네이버 태그 넣기 북마클릿 (2026-10-21 사용자: 태그 칸은 붙여넣기로 안 되고 '글 치고 Enter' 를 하나씩 해야 한다).
# 북마크바에 끌어다 두고, 네이버 발행 창의 태그 칸을 한 번 누른 뒤 누르면 복사해 둔 태그('#가 #나' 또는 쉼표)를
# 하나씩 넣고 Enter 를 친다. 클립보드를 못 읽으면 붙여넣을 칸을 띄운다. 네이버 화면이 바뀌어 안 되면 태그 버튼을 하나씩 눌러 복사한다.
NAVER_TAG_JS = """(async()=>{
function act(d){var a=d.activeElement;while(a&&a.tagName==='IFRAME'){try{d=a.contentDocument;a=d.activeElement;}catch(e){break;}}return a;}
var el=act(document);
if(!el||el.tagName!=='INPUT'){alert('네이버 발행 창의 태그 칸을 한 번 누른 뒤 다시 눌러 주세요.');return;}
var raw='';try{raw=await navigator.clipboard.readText();}catch(e){}
if(!raw||raw.indexOf('#')<0&&raw.indexOf(',')<0){raw=prompt('태그를 붙여넣으세요 (#가 #나 또는 가, 나)',raw||'');}
if(!raw)return;
var tags=raw.split(/[#,\\n]+/).map(function(t){return t.replace(/\\s+/g,'');}).filter(Boolean).slice(0,30);
var w=el.ownerDocument.defaultView,set=Object.getOwnPropertyDescriptor(w.HTMLInputElement.prototype,'value').set;
function key(type){var ev=new w.KeyboardEvent(type,{key:'Enter',code:'Enter',bubbles:true,cancelable:true});
Object.defineProperty(ev,'keyCode',{get:function(){return 13;}});Object.defineProperty(ev,'which',{get:function(){return 13;}});el.dispatchEvent(ev);}
for(var i=0;i<tags.length;i++){el.focus();set.call(el,tags[i]);el.dispatchEvent(new w.Event('input',{bubbles:true}));
key('keydown');key('keypress');key('keyup');await new Promise(function(r){setTimeout(r,150);});}
})();"""


def naver_tag_bookmarklet():
    from urllib.parse import quote
    js = " ".join(line.strip() for line in NAVER_TAG_JS.splitlines())
    return "javascript:" + quote(js, safe="()[]{};:,.'=!&|<>?+-*/_~@$^")
