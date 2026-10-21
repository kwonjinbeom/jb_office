"""data/*.json (작품마다 하나) + 환산기.js → 스킨에_붙일것.html.

작품 파일 형식: {"name": "나루토", "last": 700, "vols": [권마다 첫 화], "series": [
  {"name": "무인편", "eps": [[만화 첫 화, 끝 화, 종류(1 원작 · 2 일부 원작 · 0 오리지널)], ...], "seasons": [기마다 첫 회차] 또는 null}]}
파일 이름(naruto)이 글 본문의 [환산기: naruto] 와 맞아야 한다.
"""
import json
from pathlib import Path

HERE = Path(__file__).parent
CSS = """
.ac{border:1px solid #e3e3e3;border-radius:10px;padding:16px;margin:20px 0;font-size:15px;line-height:1.6;text-align:left}
.ac-tabs{display:grid;grid-template-columns:1fr 1fr;gap:6px;margin-bottom:10px}
.ac button{border:1px solid #ddd;background:#fff;border-radius:8px;padding:8px 0;font:inherit;color:#777;cursor:pointer}
.ac button.on{border-color:#333;color:#222;font-weight:700}
.ac-row{display:grid;grid-template-columns:1fr 1fr;gap:6px}
.ac-row.ac-3{grid-template-columns:1.4fr 1fr 1fr}
.ac-row[hidden],.ac select[hidden]{display:none}
.ac select,.ac input{width:100%;box-sizing:border-box;border:1px solid #ddd;border-radius:8px;padding:8px 10px;font:inherit;background:#fff;color:#222;margin:0}
.ac-out{margin-top:12px;padding-top:12px;border-top:1px solid #eee;min-height:58px}
.ac-big{font-size:19px;font-weight:700;color:#222}
.ac-sub{font-size:14px;color:#888}
.ac-tag{display:inline-block;margin-left:8px;padding:0 8px;border:1px solid #ccc;border-radius:99px;font-size:12px;font-weight:400;color:#666;vertical-align:3px}
""".strip()


def main():
    data = {f.stem: json.loads(f.read_text(encoding="utf-8")) for f in sorted((HERE / "data").glob("*.json"))}
    blob = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    js = (HERE / "환산기.js").read_text(encoding="utf-8").replace("__DATA__", blob)
    out = ("<!-- memorily 애니 환산기 (build.py 로 만든 파일, 직접 고치지 않는다). "
           "티스토리 관리 › 꾸미기 › 스킨 편집 › html 편집 › HTML 탭의 </body> 바로 위에 통째로 붙인다. -->\n"
           f"<style>\n{CSS}\n</style>\n<script>\n{js}</script>\n")
    (HERE / "스킨에_붙일것.html").write_text(out, encoding="utf-8")
    print("작품", ", ".join(data), "·", len(out.encode("utf-8")) // 1024, "KB")


if __name__ == "__main__":
    main()
