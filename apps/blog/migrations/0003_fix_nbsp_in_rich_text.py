# See website/migrations/0003: replace the &nbsp; the rich-text editor saved instead of spaces.

from django.db import migrations


def fix_spaces(apps, schema_editor):
    Post = apps.get_model("blog", "Post")
    for post in Post.objects.filter(body__contains="&nbsp;") | Post.objects.filter(body__contains=" "):
        post.body = post.body.replace("&nbsp;", " ").replace(" ", " ")
        post.save(update_fields=["body"])


class Migration(migrations.Migration):

    dependencies = [
        ("blog", "0002_seo_fields"),
    ]

    operations = [
        migrations.RunPython(fix_spaces, migrations.RunPython.noop),
    ]
