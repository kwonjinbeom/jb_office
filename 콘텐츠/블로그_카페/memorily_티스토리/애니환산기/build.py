"""data/*.json (작품마다 하나) + 환산기.js·환산기.css + 글모양.css·글모양.js → 스킨에_붙일것.html.

글모양은 환산기 글만이 아니라 모든 글에 걸린다 (JB Office 글 관리 변환 화면과 같은 글꼴·크기·간격, 2026-10-22).

작품 파일 형식: {"name": "나루토", "last": 700, "vols": [권마다 첫 화], "series": [
  {"name": "나루토", "eps": [[만화 첫 화, 끝 화, 종류(1 원작 · 2 일부 원작 · 0 오리지널)], ...], "seasons": [기마다 첫 회차] 또는 null}]}
파일 이름(naruto)이 글 본문의 [환산기: naruto] 와 맞아야 한다.
"""
import json
import re
from pathlib import Path

HERE = Path(__file__).parent
# 글모양.css 가 쓰는 글꼴 (JB Office 글 보기와 같은 Pretendard)
PRETENDARD = "https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css"


def main():
    data = {f.stem: json.loads(f.read_text(encoding="utf-8")) for f in sorted((HERE / "data").glob("*.json"))}
    blob = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    js = (HERE / "환산기.js").read_text(encoding="utf-8").replace("__DATA__", blob)
    look = (HERE / "글모양.css").read_text(encoding="utf-8").strip()
    # 스킨이 #아이디 + !important 로 글꼴을 박아도 이기게: :is() 는 안에서 가장 센 것(아이디 둘)의 우선순위를 갖는다
    for cls in ("jb-post", "jb-airy", "ac-post"):
        look = look.replace(f"div.contents_style.{cls}", f":is(div.contents_style.{cls},#jb-x#jb-y)")
    mark = (HERE / "글모양.js").read_text(encoding="utf-8")
    # 환산기 화면: 선택자 맨 앞 .ac 도 같은 식으로 (스킨의 button·input 꾸밈을 이기게)
    css = re.sub(r"(^|[{},])(\s*)\.ac(?=[\s{.:\[*])", r"\1\2:is(.ac,#jb-x#jb-y)",
                 (HERE / "환산기.css").read_text(encoding="utf-8").strip(), flags=re.M)
    out = ("<!-- memorily 애니 환산기 (build.py 로 만든 파일, 직접 고치지 않는다). "
           "티스토리 관리 › 꾸미기 › 스킨 편집 › html 편집 › HTML 탭의 </body> 바로 위에 통째로 붙인다 (예전 것은 지우고). -->\n"
           f'<link rel="stylesheet" href="{PRETENDARD}">\n'
           # 통계현황 (JB Office blog_ops/stats.py): 티스토리가 이 치환자를 그날 방문자 수로 바꾼다. PC 가 블로그 첫 화면에서 읽는다
           '<div id="jb-stat" hidden data-today="[##_count_today_##]" data-yesterday="[##_count_yesterday_##]" data-total="[##_count_total_##]"></div>\n'
           f"<style>\n{look}\n{css}\n</style>\n<script>\n{mark}{js}</script>\n")
    (HERE / "스킨에_붙일것.html").write_text(out, encoding="utf-8")
    print("작품", ", ".join(data), "·", len(out.encode("utf-8")) // 1024, "KB")


if __name__ == "__main__":
    main()
