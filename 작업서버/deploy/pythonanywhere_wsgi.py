# PythonAnywhere 용 WSGI 설정.
# 이 파일 내용을 PythonAnywhere Web 탭의 "WSGI configuration file"
# (/var/www/<아이디>_pythonanywhere_com_wsgi.py) 에 그대로 붙여 넣고 <아이디> 를 바꾼다.
# ~/workserver 는 ~/jb_office/작업서버 를 가리키는 영문 바로가기다 (DEPLOY.md 참고).
import os
import sys

USERNAME = "<아이디>"  # PythonAnywhere 아이디
PROJECT = f"/home/{USERNAME}/workserver"

if PROJECT not in sys.path:
    sys.path.insert(0, PROJECT)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
# 역할·비밀 값은 작업서버/.env 파일에서 읽는다 (settings.py 가 처리).

from django.core.wsgi import get_wsgi_application  # noqa: E402

application = get_wsgi_application()
