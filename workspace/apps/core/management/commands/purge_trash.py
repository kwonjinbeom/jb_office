from django.core.management.base import BaseCommand
from apps.core.trash import purge_expired


class Command(BaseCommand):
    help = "휴지통에서 7일이 지난 항목을 영구 삭제합니다."

    def handle(self, *args, **options):
        total = 0
        while True:
            count = purge_expired()
            total += count
            if count < 50:
                break
        self.stdout.write(f"{total}개 정리")
