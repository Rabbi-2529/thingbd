# The rich-text editor (Quill 2) saved every space as &nbsp;, so paragraphs could not wrap
# and pages scrolled sideways. Replace them with normal spaces in content saved so far.

from django.db import migrations


def fix_spaces(apps, schema_editor):
    for model_name in ("Service", "Project", "Page"):
        Model = apps.get_model("website", model_name)
        for obj in Model.objects.filter(body__contains="&nbsp;") | Model.objects.filter(body__contains=" "):
            obj.body = obj.body.replace("&nbsp;", " ").replace(" ", " ")
            obj.save(update_fields=["body"])


class Migration(migrations.Migration):

    dependencies = [
        ("website", "0002_seo_fields"),
    ]

    operations = [
        migrations.RunPython(fix_spaces, migrations.RunPython.noop),
    ]
