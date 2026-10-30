"""플랫폼별 붙여넣기: 변환본을 통째로 복사해 그 사이트 글쓰기 화면에 붙이는 방법 (2026-10-16 조사, 근거는 포스팅자동화/13 문서).

변환본은 늘 마크다운(또는 이미 만든 HTML)으로 저장하고, 복사할 때 플랫폼에 맞는 꼴로 바꾼다.
- 티스토리: 티스토리 글쓰기와 같은 HTML(표·인용은 인라인 style, 머리글은 굵은 보통 칸) → HTML 모드에 붙이고 기본모드로 돌아와 확인
  (꾸밈 없는 HTML 은 표 테두리가 빠지고 머리글 줄이 표 밖으로 빠져 2026-10-20 바꿨다)
- 네이버: 서식 그대로(인라인 style) → 본문 Ctrl+V (HTML 입력 모드가 없다)
- 블로거: 티스토리와 같은 HTML → HTML 보기에 붙이고 작성 보기로 돌아가지 않는다 (작성 보기는 HTML 을 다시 쓴다)
- 워드프레스: class 를 단 HTML 을 '사용자 정의 HTML' 블록 하나로 (<!-- wp:html -->) → 코드 편집기에 붙인다.
  모양은 콘텐츠/블로그_카페/워드프레스/글모양.css 를 그 블록 안 <style> 로 함께 넣는다 (wp_looks, 2026-10-26 — '추가 CSS'는 편집 화면에 안 보인다)
"""
import re

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
        "tags": "발행 창의 태그 칸 (붙여넣기로는 한 태그로 붙는다 → '블로그 넣기' 북마크나 태그 하나씩 복사 + Enter)",
        "after": "맨 위 결론 인용은 네이버 '따옴표' 인용구로 바뀐다 (그대로 둔다) · 소제목 줄을 '소제목'으로 다시 지정 · "
                 "첫 사진을 지우고 '대표 사진'으로 받은 파일을 그 자리에 올리기 (붙여넣은 사진은 바깥 주소라 대표 사진·홈 썸네일이 안 된다) · 남은 사진 자리에 직접 업로드(빈 1칸 표 지우기) · 코드는 소스코드 칸에 · "
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
        "where": "새 글 → 오른쪽 위 ⋮ → 코드 편집기에 본문 HTML 을 붙이고 '코드 편집기 나가기' (사용자 정의 HTML 블록 하나가 된다)",
        "body": [
            {"kind": "html", "label": "본문 HTML (코드 편집기)", "msg": "본문 HTML 을 복사했습니다. 워드프레스 코드 편집기에 붙여넣으세요.",
             "hint": "⋮ → 코드 편집기 → 붙여넣기"},
            {"kind": "raw", "label": "본문 마크다운", "msg": "본문 마크다운을 복사했습니다.", "hint": "카드·목차 모양 없이 블록으로 쓸 때"},
        ],
        "tags": "오른쪽 '글' 탭의 태그 칸 (쉼표)",
        "after": "글꼴·색은 붙인 HTML 안에 들어 있다 (블록 위 '미리보기'로 확인) · 카테고리 · 슬러그(영문 짧게) · "
                 "대표 이미지: '대표 사진' 버튼으로 받은 파일을 오른쪽 '대표 이미지 설정 → 파일 업로드'에 끌어다 놓고 대체 텍스트 붙이기 · "
                 "요약(발췌)에 소개 한두 문장",
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
    return _bookmarklet(NAVER_TAG_JS)


def _bookmarklet(source):
    from urllib.parse import quote
    js = " ".join(line.strip() for line in source.splitlines())
    return "javascript:" + quote(js, safe="()[]{};:,.'=!&|<>?+-*/_~@$^")


# 한 번에 넣기 (2026-10-27 사용자: 복사 버튼 하나 + 북마크 하나로 제목·본문·태그를). '한 번에 복사'가 클립보드 글자칸에
# ALL_MARK + {title, html, tags} 를, 서식칸에 본문 HTML 을 담는다 (북마크가 안 되면 네이버 본문은 Ctrl+V 로 그대로 붙는다).
# 북마크 하나가 사이트를 보고 나눈다. 태그가 따로 있는 네이버(발행 창)·블로거(라벨)는 그 칸을 누르고 같은 북마크를 한 번 더.
# - 티스토리: 제목 칸 · 본문(기본모드 TinyMCE setContent — HTML 모드에 붙이고 돌아온 것과 같다) · 태그 칸에 하나씩 Enter
# - 블로거: 제목 칸 · HTML 보기(CodeMirror)에 본문. 라벨 칸을 누르고 다시 누르면 라벨을 쉼표로
# - 네이버: 스마트에디터 ONE 제목·본문에 붙여넣기 이벤트 (PC 에서 못 열어 본 화면 — 안 되면 알리고 Ctrl+V 로).
#   발행 창 태그 칸을 누르고 다시 누르면 태그를 하나씩 Enter
# 변환본의 그림 줄을 감싼 <div>·<p>·<center> 를 벗긴다 (2026-10-27 사용자: 코스피 시황 노트에 그림 대신 주소가 보였다 —
# HTML 블록 안의 ![설명](주소) 는 마크다운으로 풀리지 않는다. 가운데 정렬은 서버가 한다).
_WRAPPED_IMAGE = re.compile(r"<(div|p|center)\b[^>]*>\s*(!\[[^\]\n]*\]\([^)\s]+\)(?:\s*\n\*[^\n]+\*)?)\s*</\1>", re.I)


def unwrap_images(text):
    return _WRAPPED_IMAGE.sub(lambda m: m.group(2), text or "")


# 글 끝 'YYYY-MM-DD 기준, 바뀌면 고칩니다.' 줄 (2026-10-28 사용자: "이거 지워줘" — blog_types 0048 로 컨셉·옛 글에서 뺐는데
# 2026-10-31 작가가 옛 원고를 흉내 내 다시 썼다 → 프롬프트가 아니라 변환본을 받을 때 · 워드프레스로 그릴 때 코드로 뺀다)
ASOF_LINE = re.compile(r"(?:\r?\n)*^[ \t]*\*?\d{4}-\d{2}-\d{2} 기준, ?바뀌면 고(?:칩니다|친다|침)\.?\*?[ \t]*$", re.M)


def drop_asof(text):
    return ASOF_LINE.sub("", text or "")


ALL_MARK = "JBPASTE1\n"
PASTE_JS = """(async()=>{
var MARK='JBPASTE1';
function act(d){var a=d.activeElement;while(a&&a.tagName==='IFRAME'){try{d=a.contentDocument;a=d.activeElement;}catch(e){break;}}return a;}
function wait(ms){return new Promise(function(r){setTimeout(r,ms);});}
function note(m){var b=document.createElement('div');b.textContent=m;b.style.cssText='position:fixed;z-index:2147483647;left:50%;top:16px;transform:translateX(-50%);background:#1f2937;color:#fff;padding:10px 16px;border-radius:8px;font:14px sans-serif;box-shadow:0 4px 12px rgba(0,0,0,.25)';document.body.appendChild(b);setTimeout(function(){b.remove();},4000);}
function setVal(el,v){var p=Object.getPrototypeOf(el);el.focus();Object.getOwnPropertyDescriptor(p,'value').set.call(el,v);el.dispatchEvent(new Event('input',{bubbles:true}));el.dispatchEvent(new Event('change',{bubbles:true}));}
async function enterTags(el,tags){var w=el.ownerDocument.defaultView,set=Object.getOwnPropertyDescriptor(w.HTMLInputElement.prototype,'value').set;
function key(type){var ev=new w.KeyboardEvent(type,{key:'Enter',code:'Enter',bubbles:true,cancelable:true});
Object.defineProperty(ev,'keyCode',{get:function(){return 13;}});Object.defineProperty(ev,'which',{get:function(){return 13;}});el.dispatchEvent(ev);}
for(var i=0;i<tags.length;i++){el.focus();set.call(el,tags[i]);el.dispatchEvent(new w.Event('input',{bubbles:true}));
key('keydown');key('keypress');key('keyup');await wait(150);}}
var raw='';try{raw=await navigator.clipboard.readText();}catch(e){}
var data=null;if(raw.indexOf(MARK)===0){try{data=JSON.parse(raw.slice(MARK.length));}catch(e){}}
var tags=data?data.tags:raw.split(/[#,\\n]+/).map(function(t){return t.replace(/\\s+/g,'');}).filter(Boolean);
tags=tags.slice(0,30);
var host=location.hostname,el=act(document);
function need(){if(!data){alert('변환 화면에서 「한 번에 복사」를 먼저 누른 뒤 다시 눌러 주세요.');return true;}return false;}
if(/(^|\\.)tistory\\.com$/.test(host)){
if(need())return;var t=document.querySelector('#post-title-inp');
if(!t||!window.tinymce||!tinymce.activeEditor){alert('티스토리 글쓰기 화면에서 눌러 주세요.');return;}
if([].some.call(document.querySelectorAll('.CodeMirror'),function(c){return c.offsetParent;})){alert('기본모드로 바꾼 뒤 다시 눌러 주세요.');return;}
setVal(t,data.title);var ed=tinymce.activeEditor;ed.setContent(data.html);ed.undoManager.add();ed.fire('change');ed.setDirty(true);
var tg=document.querySelector('#tagText');if(tg&&tags.length)await enterTags(tg,tags);
note('제목·본문·태그 '+tags.length+'개를 넣었습니다. 사진·대표 이미지를 확인하세요.');return;}
if(/(^|\\.)blogger\\.com$/.test(host)){
if(need())return;
if(el&&el.tagName==='TEXTAREA'&&/라벨|label/i.test((el.placeholder||'')+(el.getAttribute('aria-label')||''))){
el.select();document.execCommand('insertText',false,tags.join(', '));note('라벨 '+tags.length+'개를 넣었습니다.');return;}
var bt=[].filter.call(document.querySelectorAll('input[aria-label="제목"],input[aria-label="Title"]'),function(i){return i.offsetParent;})[0];
var cm=[].filter.call(document.querySelectorAll('.CodeMirror'),function(c){return c.offsetParent&&c.CodeMirror;})[0];
if(!bt){alert('블로거 글쓰기 화면에서 눌러 주세요.');return;}
if(!cm){alert('왼쪽 위 연필 → HTML 보기로 바꾼 뒤 다시 눌러 주세요.');return;}
function putTitle(){bt.focus();bt.select();try{document.execCommand('insertText',false,data.title);}catch(e){}if(bt.value!==data.title)setVal(bt,data.title);bt.dispatchEvent(new Event('change',{bubbles:true}));bt.blur();}
putTitle();cm.CodeMirror.setValue(data.html);await wait(400);if(bt.value!==data.title)putTitle();
note('제목·본문을 넣었습니다. 라벨 칸을 누르고 북마크를 한 번 더 누르세요.');return;}
if(/(^|\\.)naver\\.com$/.test(host)){
if(el&&el.tagName==='INPUT'&&!el.closest('.se-documentTitle')){
if(!tags.length){alert('태그가 없습니다. 「한 번에 복사」나 ③ 태그를 먼저 누르세요.');return;}
await enterTags(el,tags);return;}
if(need())return;var d=document,f=d.querySelector('#mainFrame');if(f){try{d=f.contentDocument||d;}catch(e){}}
var w=d.defaultView;
var tp=d.querySelector('.se-documentTitle .se-text-paragraph');
var bp=d.querySelectorAll('.se-component.se-text .se-text-paragraph');bp=bp[bp.length-1];
if(!tp||!bp){alert('네이버 글쓰기 화면에서 눌러 주세요.');return;}
function paste(p,html,text){['mousedown','mouseup','click'].forEach(function(t){p.dispatchEvent(new w.MouseEvent(t,{bubbles:true,cancelable:true,view:w}));});
var s=w.getSelection(),r=d.createRange();r.selectNodeContents(p);r.collapse(false);s.removeAllRanges();s.addRange(r);
var dt=new w.DataTransfer();if(html)dt.setData('text/html',html);dt.setData('text/plain',text);
(act(d)||p).dispatchEvent(new w.ClipboardEvent('paste',{clipboardData:dt,bubbles:true,cancelable:true}));}
var before=d.body.innerText.length;paste(tp,'',data.title);await wait(300);var x=d.createElement('div');x.innerHTML=data.html;paste(bp,data.html,x.textContent);await wait(500);
if(d.body.innerText.length-before<data.title.length){alert('네이버 에디터가 붙여넣기를 받지 않았습니다. 제목은 ① 제목, 본문은 Ctrl+V 로 붙여 주세요 (서식 그대로 붙습니다).');return;}
note('제목·본문을 넣었습니다. 발행 창 태그 칸을 누르고 북마크를 한 번 더 누르세요.');return;}
alert('티스토리·블로거·네이버 글쓰기 화면에서 눌러 주세요.');
})();"""


def paste_bookmarklet():
    return _bookmarklet(PASTE_JS)


def paste_all(title, html, tags):
    """'한 번에 복사' 글자칸: 북마크가 읽는 표시 + JSON. 태그는 '#가 #나'·'가, 나' 어느 꼴이든 목록으로."""
    import json
    import re
    items = [t.strip() for t in re.split(r"[#,\n]+", tags or "") if t.strip()]
    return ALL_MARK + json.dumps({"title": title, "html": html, "tags": items}, ensure_ascii=False)
