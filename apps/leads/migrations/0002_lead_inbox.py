# Lead inbox (Phase 4): the single `notes` text field becomes a LeadNote timeline.

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def copy_notes_to_timeline(apps, schema_editor):
    Lead = apps.get_model("leads", "Lead")
    LeadNote = apps.get_model("leads", "LeadNote")
    LeadNote.objects.bulk_create(
        LeadNote(lead_id=pk, kind="note", text=text)
        for pk, text in Lead.objects.exclude(legacy_notes="").values_list("pk", "legacy_notes")
    )


def copy_timeline_to_notes(apps, schema_editor):
    Lead = apps.get_model("leads", "Lead")
    LeadNote = apps.get_model("leads", "LeadNote")
    for lead in Lead.objects.all():
        texts = LeadNote.objects.filter(lead_id=lead.pk, kind="note").order_by("created_at").values_list("text", flat=True)
        lead.legacy_notes = "\n\n".join(texts)
        lead.save(update_fields=["legacy_notes"])


class Migration(migrations.Migration):

    dependencies = [
        ('leads', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RenameField(model_name='lead', old_name='notes', new_name='legacy_notes'),
        migrations.CreateModel(
            name='LeadNote',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('kind', models.CharField(choices=[('note', 'Note'), ('status', 'Status change')], default='note', max_length=10)),
                ('text', models.TextField(max_length=4000)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('author', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                ('lead', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='notes', to='leads.lead')),
            ],
            options={
                'ordering': ['-created_at', '-id'],
            },
        ),
        migrations.RunPython(copy_notes_to_timeline, copy_timeline_to_notes),
        migrations.RemoveField(model_name='lead', name='legacy_notes'),
        migrations.AddField(
            model_name='lead',
            name='page_url',
            field=models.CharField(blank=True, max_length=255, verbose_name='Sent from page'),
        ),
        migrations.AlterField(
            model_name='lead',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, db_index=True),
        ),
    ]
