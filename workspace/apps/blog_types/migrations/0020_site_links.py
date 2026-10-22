"""블로그·카페 화면 위쪽 바로가기 (2026-10-23 사용자). 처음 값은 운영 화면 블로그 중 주소가 있는 것 (보류 제외), 운영 순서대로."""

from django.db import migrations, models


def seed(apps, schema_editor):
    Blog, SiteLink = apps.get_model("blog_rules", "Blog"), apps.get_model("blog_types", "SiteLink")
    if SiteLink.objects.exists():
        return
    blogs = (Blog.objects.filter(deleted_at__isnull=True).exclude(address="").exclude(status="hold")
             .order_by("order", "pk"))
    SiteLink.objects.bulk_create([SiteLink(name=b.name[:30], url=b.address, order=i) for i, b in enumerate(blogs)])


class Migration(migrations.Migration):

    dependencies = [
        ('blog_types', '0019_nunip_site_categories'),
        ('blog_rules', '0009_site_targets'),
    ]

    operations = [
        migrations.CreateModel(
            name='SiteLink',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=30, verbose_name='이름')),
                ('url', models.URLField(max_length=500, verbose_name='주소')),
                ('order', models.PositiveIntegerField(default=0, verbose_name='순서')),
            ],
            options={
                'verbose_name': '바로가기',
                'verbose_name_plural': '바로가기',
                'ordering': ['order', 'pk'],
            },
        ),
        migrations.RunPython(seed, migrations.RunPython.noop),
    ]
