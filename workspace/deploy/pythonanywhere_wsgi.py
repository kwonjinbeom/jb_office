# PythonAnywhere 용 WSGI 설정.
# 이 파일 내용을 PythonAnywhere Web 탭의 "WSGI configuration file"
# (/var/www/<아이디>_pythonanywhere_com_wsgi.py) 에 그대로 붙여 넣고 <아이디> 를 바꾼다.
import os
import sys

USERNAME = "<아이디>"  # PythonAnywhere 아이디
PROJECT = f"/home/{USERNAME}/jb_office/workspace"

if PROJECT not in sys.path:
    sys.path.insert(0, PROJECT)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
# 역할·비밀 값은 workspace/.env 파일에서 읽는다 (settings.py 가 처리).

from django.core.wsgi import get_wsgi_application  # noqa: E402

application = get_wsgi_application()
