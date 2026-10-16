import os
import sys

from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.core"
    verbose_name = "메뉴"

    def ready(self):
        # runserver 로 실제 서빙하는 프로세스에서만 백그라운드 git 동기화를 켠다.
        # (autoreload 가 켜져 있으면 부모 프로세스는 RUN_MAIN 이 없고 자식만 'true')
        if "runserver" not in sys.argv:
            return
        is_serving_process = os.environ.get("RUN_MAIN") == "true" or "--noreload" in sys.argv
        if not is_serving_process:
            return
        from . import autosync

        autosync.start_background_sync()
