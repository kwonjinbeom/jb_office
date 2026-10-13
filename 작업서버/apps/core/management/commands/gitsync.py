from django.core.management.base import BaseCommand

from apps.core import gitstate


class Command(BaseCommand):
    help = "저장소의 모든 변경을 커밋하고 push 한다. (python manage.py gitsync -m '메시지')"

    def add_arguments(self, parser):
        parser.add_argument("-m", "--message", help="커밋 메시지")

    def handle(self, *args, **options):
        result = gitstate.run_sync(reason="manage.py", message=options.get("message"))
        if result["ok"]:
            self.stdout.write(self.style.SUCCESS(f"ok: {result.get('message', 'no changes')}"))
        else:
            self.stderr.write(self.style.ERROR(f"failed: {result.get('error')}"))
