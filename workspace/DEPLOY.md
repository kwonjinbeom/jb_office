# PythonAnywhere 배포 (무료 Beginner 계정)

목표: `https://<아이디>.pythonanywhere.com` 에서 작업서버가 항상 떠 있고, DB 는 서버에만 있다.
PC 와 폰 모두 브라우저로 이 주소에 접속해 데이터를 고친다. 코드는 GitHub 를 거쳐 서버가 pull 받는다.

아래에서 `<아이디>` 는 PythonAnywhere 로그인 아이디다. 이메일이 아니다.
서버의 프로젝트 경로는 `/home/<아이디>/jb_office/workspace` 다. (PythonAnywhere 는 경로에 한글을 허용하지 않는다.)

## 1. 처음 한 번: 서버 준비 (Bash 콘솔)

PythonAnywhere 사이트 → **Consoles** → **Bash** 를 열고 한 줄씩 실행한다.

```bash
cd ~
git clone https://github.com/kwonjinbeom/jb_office.git
mkdir -p ~/data
cd ~/jb_office/workspace
python3.12 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env
nano .env
```

`nano` 에서 `.env` 를 아래처럼 고친다 (`<아이디>` 4곳 교체, 비밀 키는 아무 긴 문자열). 저장은 Ctrl+O, Enter, 종료는 Ctrl+X.

```
WORKSERVER_ROLE=server
DJANGO_SECRET_KEY=여기에-긴-무작위-문자열
DJANGO_ALLOWED_HOSTS=<아이디>.pythonanywhere.com
DJANGO_CSRF_TRUSTED_ORIGINS=https://<아이디>.pythonanywhere.com
DATABASE_PATH=/home/<아이디>/data/db.sqlite3
DEPLOY_RELOAD_TOUCH_FILE=/var/www/<아이디>_pythonanywhere_com_wsgi.py
```

비밀 키는 이 명령으로 만들어 붙여 넣으면 된다.

```bash
python3.12 -c "import secrets; print(secrets.token_urlsafe(50))"
```

이어서 DB 를 만들고 로그인 계정을 넣는다. ('내 아이디어'는 일일 아이디어에서 직접 담은 것만 두므로 초기 데이터는 넣지 않는다.)

```bash
.venv/bin/python manage.py migrate
.venv/bin/python manage.py createsuperuser
.venv/bin/python manage.py collectstatic --noinput
```

`createsuperuser` 가 묻는 아이디·비밀번호가 작업서버 로그인 계정이 된다. 이메일은 비워도 된다.

## 2. 처음 한 번: 웹앱 등록 (Web 탭)

1. **Web** 탭 → **Add a new web app** → 도메인 확인 → **Manual configuration** → **Python 3.12** (가상환경을 만든 버전과 같아야 한다).
2. 같은 페이지에서 아래 항목을 채운다.

| 항목 | 값 |
|---|---|
| Source code | `/home/<아이디>/jb_office/workspace` |
| Working directory | `/home/<아이디>/jb_office/workspace` |
| Virtualenv | `/home/<아이디>/jb_office/workspace/.venv` |

3. **WSGI configuration file** 링크를 눌러 열고, 내용을 전부 지운 뒤 저장소의 `workspace/deploy/pythonanywhere_wsgi.py` 내용을 붙여 넣는다. `USERNAME = "<아이디>"` 를 고치고 저장한다.
4. **Static files** 에 한 줄 추가: URL `/static/` → Directory `/home/<아이디>/jb_office/workspace/staticfiles`.
5. 맨 위 초록색 **Reload** 버튼을 누른다.
6. `https://<아이디>.pythonanywhere.com` 에 접속해 로그인 화면이 나오면 성공.

## 3. 이후 코드가 바뀌었을 때 (콘솔 필요 없음)

두 경로가 있고, 둘 다 `git pull` → 패키지 설치(requirements) → `migrate` → `collectstatic` → 앱 재시작을 한 번에 한다.

- **자동**: GitHub `main` 에 push 되면 GitHub 가 서버의 `/deploy/webhook/` 을 호출하고 서버가 스스로 반영한다.
- **수동**: 서버 홈 화면의 **서버 코드 갱신** 버튼. 웹훅이 실패했거나 바로 확인하고 싶을 때.

> **웹훅은 켜져 있다 (2026-10-15 확인, 최근 응답 모두 200).** 평소에는 버튼도 콘솔 `migrate` 도 필요 없다. 에이전트는 사용자에게 이것을 시키지 않고, push 뒤 `gh api repos/kwonjinbeom/jb_office/hooks/<id>/deliveries` 로 `deployed <커밋>` 응답을 직접 확인한다.

### 3-1. 자동 반영 처음 한 번 켜기 (화면에서)

1. 작업서버 좌측 메뉴 **설정** → **비밀값 만들기** 를 누른다. 비밀값과 Payload URL 이 화면에 나온다.
2. GitHub 저장소 → **Settings** → **Webhooks** → **Add webhook** 에 입력한다.

| 항목 | 값 |
|---|---|
| Payload URL | 설정 화면에 표시된 주소 (`https://<아이디>.pythonanywhere.com/deploy/webhook/`) |
| Content type | `application/json` |
| Secret | 설정 화면의 비밀값 |
| Which events | **Just the push event** |

3. Add webhook 을 누르면 GitHub 가 ping 을 보낸다. Recent Deliveries 가 초록 체크(200, 본문 `pong`)면 성공.
4. 이후 push 마다 Recent Deliveries 에 `deployed <해시>` 가 남는다. 응답이 10초를 넘겨 GitHub 쪽에 timeout 으로 표시돼도 서버 반영은 진행된다.

웹훅은 `main` 브랜치 push 만 처리한다. 비밀값은 DB(앱 설정)에 저장되며 `.env` 의 `DEPLOY_WEBHOOK_SECRET` 은 예비용이다.

## 4. 데이터 백업

DB 는 `~/data/db.sqlite3` 하나다. **Files** 탭에서 그 파일을 내려받으면 백업이다.
PC 로 가져와 보고 싶으면 내려받은 파일을 `workspace/db.sqlite3` 에 두고 `run.bat` 을 실행하면 된다.

## 5. 무료 계정에서 알아 둘 것

- 3개월마다 PythonAnywhere 사이트에 로그인해야 앱이 꺼지지 않는다. 메일로 알려 준다.
- 무료 계정은 외부 인터넷 접속이 허용 목록으로 제한된다. github.com 은 허용되어 있어 pull 은 된다.
- CPU 시간이 하루 100초로 제한된다. 개인 도구로는 충분하다.
- 백그라운드 스레드(자동 동기화)는 서버 역할에서 꺼져 있다. 서버는 push 하지 않는다.
