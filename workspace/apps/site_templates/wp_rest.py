"""워드프레스 초안 올리기 (2026-10-26 사용자: 변환이 끝나면 PC claude 가 REST API 로 초안을 올린다).

PC 에서만 돈다: 서버(PythonAnywhere 무료)는 외부 접속 허용 목록 때문에 jinbaam.com 에 닿지 않는다.
  1. 서버 api_wp 에서 재료(제목 · 붙일 HTML · 카테고리 · 태그 · 슬러그 · 발췌 · 첫 사진)를 받는다
  2. 첫 사진을 미디어로 올려 대표 이미지로 · 카테고리는 이름으로 찾고 · 태그는 없으면 만든다
  3. 초안을 만들거나(처음) 고친다(다시 변환). 이미 발행·예약한 글은 건드리지 않는다
  4. 올린 글 번호를 서버에 돌려준다
인증은 워드프레스 애플리케이션 비밀번호 (사용자 › 프로필 › 애플리케이션 비밀번호): workspace/.env 의 WP_URL · WP_USER · WP_APP_PASSWORD.
.env 는 git 에 올라가지 않는다. 명령: manage.py wp_draft (site_templates/management/commands/wp_draft.py).
"""
import base64
import html
import json
import mimetypes
import os
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from urllib.parse import unquote

from django.conf import settings

from . import prompt

TIMEOUT = 40
UA = "jb_office wp_draft"
EDITABLE = {"draft", "pending", "auto-draft"}  # 이 상태만 고친다 (발행·예약·비공개는 사용자가 손댄 글)


class WPError(Exception):
    pass


def config():
    """(사이트 주소, 사용자, 비밀번호) — 하나라도 없으면 None."""
    url = os.environ.get("WP_URL", "https://jinbaam.com").rstrip("/")
    user, password = os.environ.get("WP_USER", ""), os.environ.get("WP_APP_PASSWORD", "")
    return (url, user, password.replace(" ", "")) if user and password else None


class Client:
    def __init__(self, url, user, password):
        self.base = url.rstrip("/") + "/wp-json/wp/v2"
        self.site = url.rstrip("/")
        self.auth = "Basic " + base64.b64encode(f"{user}:{password}".encode()).decode()

    def call(self, method, path, data=None, raw=None, headers=None):
        url = path if path.startswith("http") else self.base + path
        head = {"Authorization": self.auth, "User-Agent": UA, "Accept": "application/json"}
        body = raw
        if data is not None:
            body = json.dumps(data, ensure_ascii=False).encode("utf-8")
            head["Content-Type"] = "application/json; charset=utf-8"
        head.update(headers or {})
        req = urllib.request.Request(url, data=body, headers=head, method=method)
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as res:
                return json.loads(res.read().decode("utf-8") or "null")
        except urllib.error.HTTPError as e:
            text = e.read().decode("utf-8", "replace")
            try:
                err = json.loads(text)
            except ValueError:
                err = {"message": text[:200]}
            raise WPError(f"{e.code} {err.get('code', '')} {err.get('message', '')}".strip(), err) from None

    def me(self):
        return self.call("GET", "/users/me?context=edit")

    def category_ids(self, name):
        cats = self.call("GET", "/categories?per_page=100&hide_empty=false")
        return [c["id"] for c in cats if html.unescape(c.get("name", "")).strip() == name.strip()]

    def tag_ids(self, names):
        ids = []
        for name in names:
            found = self.call("GET", "/tags?per_page=100&search=" + urllib.parse.quote(name))
            hit = next((t["id"] for t in found if html.unescape(t.get("name", "")).strip().lower() == name.strip().lower()), None)
            if hit is None:
                try:
                    hit = self.call("POST", "/tags", {"name": name})["id"]
                except WPError as e:  # 이미 있는 태그 (검색이 못 찾은 경우)
                    data = e.args[1] if len(e.args) > 1 else {}
                    hit = (data.get("data") or {}).get("term_id")
                    if hit is None:
                        raise
            ids.append(hit)
        return ids

    def upload(self, data, filename, ctype, alt=""):
        media = self.call("POST", "/media", raw=data, headers={
            "Content-Type": ctype, "Content-Disposition": f'attachment; filename="{filename}"'})
        if alt:
            self.call("POST", f"/media/{media['id']}", {"alt_text": alt})
        return media["id"]


def image_bytes(src, pk):
    """첫 사진 바이트·파일 이름·종류. 저장소의 변환그림은 PC 디스크에서, 다른 주소는 내려받는다."""
    from .views import HERO_TYPES, _hero_name
    if src.startswith(prompt.FIGURE_URL):
        base = (Path(settings.REPO_ROOT) / prompt.FIGURE_DIR).resolve()
        path = (Path(settings.REPO_ROOT) / unquote(src[len(prompt.FIGURE_URL):].split("?", 1)[0])).resolve()
        if path.is_file() and base in path.parents:
            ctype = mimetypes.guess_type(path.name)[0] or "image/jpeg"
            return path.read_bytes(), _hero_name(src, pk), ctype
    req = urllib.request.Request(src, headers={"User-Agent": "Mozilla/5.0 (jb_office)"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as res:
        ctype = res.headers.get_content_type()
        data = res.read()
    if ctype not in HERO_TYPES:
        raise WPError(f"사진이 아닙니다: {ctype}")
    return data, _hero_name(src, pk, HERO_TYPES[ctype]), ctype


def fetch_job(api_url):
    req = urllib.request.Request(api_url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as res:
        return json.loads(res.read().decode("utf-8"))


def report(api_url, wp_post_id):
    body = urllib.parse.urlencode({"wp_post_id": wp_post_id}).encode()
    req = urllib.request.Request(api_url, data=body, method="POST", headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as res:
        return res.read().decode("utf-8")


def draft(api_url, client, log=print):
    """초안 하나 올리기. 돌려주는 값: 한 줄 결과 (편집 주소 포함)."""
    job = fetch_job(api_url)
    post_id, existing = job.get("wp_post_id"), None
    if post_id:
        try:
            existing = client.call("GET", f"/posts/{post_id}?context=edit")
        except WPError as e:
            if not str(e).startswith("404"):
                raise
            post_id = None  # 워드프레스에서 지운 초안 → 새로 만든다
    if existing and existing.get("status") not in EDITABLE:
        return f"건너뜀 · 번호 {job['id']} · 워드프레스 글 {post_id} 은 이미 {existing.get('status')} (발행한 글은 고치지 않는다)"

    payload = {"title": job["title"], "content": job["content"], "status": "draft", "excerpt": job.get("excerpt", "")}
    if job.get("slug"):
        payload["slug"] = job["slug"]
    cats = client.category_ids(job.get("category", ""))
    if cats:
        payload["categories"] = cats
    else:
        log(f"  카테고리 '{job.get('category')}' 를 워드프레스에서 못 찾아 넣지 않았습니다")
    if job.get("tags"):
        payload["tags"] = client.tag_ids(job["tags"])
    hero = job.get("hero")
    if hero and not (existing and existing.get("featured_media")):
        try:
            data, filename, ctype = image_bytes(hero["src"], job["id"])
            payload["featured_media"] = client.upload(data, filename, ctype, hero.get("alt", ""))
        except (WPError, OSError, urllib.error.URLError) as e:
            log(f"  대표 이미지를 올리지 못했습니다 ({e}) — 초안은 그대로 올립니다")

    post = client.call("POST", f"/posts/{post_id}" if post_id else "/posts", payload)
    report(api_url, post["id"])
    edit = f"{client.site}/wp-admin/post.php?post={post['id']}&action=edit"
    return f"ok · 번호 {job['id']} · 워드프레스 초안 {post['id']} {'고침' if post_id else '새로 만듦'} · {edit}"
