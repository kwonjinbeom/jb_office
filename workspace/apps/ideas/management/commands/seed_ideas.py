from django.core.management.base import BaseCommand

from apps.ideas.models import Idea
from apps.ideas.seed_data import IDEAS


class Command(BaseCommand):
    help = "시장조사 문서의 후보 C01~C35 를 아이디어 테이블에 적재한다. 기본은 없는 코드만 추가."

    def add_arguments(self, parser):
        parser.add_argument(
            "--overwrite",
            action="store_true",
            help="이미 있는 코드도 시드 값으로 덮어쓴다 (화면에서 고친 내용이 사라진다)",
        )

    def handle(self, *args, **options):
        created = updated = skipped = 0
        for row in IDEAS:
            data = dict(row)
            code = data.pop("code")
            obj = Idea.objects.filter(code=code).first()
            if obj is None:
                Idea.objects.create(code=code, **data)
                created += 1
            elif options["overwrite"]:
                for key, value in data.items():
                    setattr(obj, key, value)
                obj.save()
                updated += 1
            else:
                skipped += 1
        self.stdout.write(
            self.style.SUCCESS(f"seed_ideas: created={created} updated={updated} skipped={skipped}")
        )
