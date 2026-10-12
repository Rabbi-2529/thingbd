from django.contrib.auth import get_user_model
from django.core import mail
from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from apps.core.models import SiteSettings
from apps.leads.models import Lead, LeadNote


def make_lead(name="Rahim Uddin", email="rahim@example.com", **extra):
    return Lead.objects.create(name=name, email=email, message="Need an ERP", **extra)


class LeadInboxTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.editor = User.objects.create_user("editor", "e@example.com", "Str0ng-pass!", is_staff=True, first_name="Ed")
        cls.other = User.objects.create_user("other", "o@example.com", "Str0ng-pass!", is_staff=True)

    def setUp(self):
        self.client.force_login(self.editor)
        self.lead = make_lead(phone="+880 1711-000000", company="Acme", service="Web Development", page_url="/")

    def test_list_and_detail_render(self):
        response = self.client.get(reverse("dashboard:leads_list"))
        self.assertContains(response, "Rahim Uddin")
        self.assertContains(response, self.lead.get_dashboard_url())
        self.assertNotContains(response, reverse("dashboard:leads_list") + "add/")  # no Add button
        detail = self.client.get(self.lead.get_dashboard_url())
        self.assertContains(detail, "Need an ERP")
        self.assertContains(detail, "https://wa.me/8801711000000")

    def test_add_and_generic_edit_are_disabled(self):
        self.assertEqual(self.client.get(reverse("dashboard:leads_add")).status_code, 404)
        self.assertEqual(self.client.get(reverse("dashboard:leads_edit", args=[self.lead.pk])).status_code, 404)

    def test_sidebar_badge_counts_new_leads(self):
        make_lead(name="Second", email="b@example.com")
        response = self.client.get(reverse("dashboard:index"))
        self.assertContains(response, 'class="nav-badge" title="2 new"')

    def test_change_status_logs_activity(self):
        url = self.lead.get_dashboard_url()
        response = self.client.post(url, {"action": "status", "status": "contacted"})
        self.assertRedirects(response, url)
        self.lead.refresh_from_db()
        self.assertEqual(self.lead.status, "contacted")
        note = self.lead.notes.get()
        self.assertEqual(note.kind, LeadNote.Kind.STATUS)
        self.assertEqual(note.author, self.editor)
        self.assertIn("New to Contacted", note.text)

    def test_invalid_or_same_status_is_ignored(self):
        url = self.lead.get_dashboard_url()
        self.client.post(url, {"action": "status", "status": "new"})
        self.client.post(url, {"action": "status", "status": "bogus"})
        self.assertFalse(self.lead.notes.exists())

    def test_add_and_delete_notes(self):
        url = self.lead.get_dashboard_url()
        self.client.post(url, {"action": "note", "text": "Called, sending quote Friday"})
        note = self.lead.notes.get()
        self.assertContains(self.client.get(url), "Called, sending quote Friday")
        # someone else's note can't be deleted by a non-superuser
        self.client.force_login(self.other)
        self.client.post(url, {"action": "delete_note", "note": note.pk})
        self.assertTrue(LeadNote.objects.filter(pk=note.pk).exists())
        self.client.force_login(self.editor)
        self.client.post(url, {"action": "delete_note", "note": note.pk})
        self.assertFalse(LeadNote.objects.filter(pk=note.pk).exists())

    def test_empty_note_rejected(self):
        response = self.client.post(self.lead.get_dashboard_url(), {"action": "note", "text": "  "})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(self.lead.notes.exists())

    def test_filters(self):
        make_lead(name="Karim", email="k@example.com", service="SEO & Growth", status="won")
        url = reverse("dashboard:leads_list")
        response = self.client.get(url, {"lead_status": "won"})
        self.assertContains(response, "Karim")
        self.assertNotContains(response, "Rahim Uddin")
        response = self.client.get(url, {"service": "Web Development"})
        self.assertContains(response, "Rahim Uddin")
        self.assertNotContains(response, "Karim")

    def test_bulk_status_change(self):
        second = make_lead(name="Second", email="b@example.com")
        self.client.post(reverse("dashboard:leads_bulk"), {"action": "mark_won", "ids": [self.lead.pk, second.pk]})
        self.assertEqual(Lead.objects.filter(status="won").count(), 2)
        self.assertEqual(LeadNote.objects.filter(kind="status").count(), 2)

    def test_csv_export_of_filtered_leads(self):
        make_lead(name="=HYPERLINK(\"http://evil\")", email="x@example.com", status="lost")
        response = self.client.get(reverse("dashboard:leads_export"), {"lead_status": "lost"})
        self.assertEqual(response["Content-Type"], "text/csv; charset=utf-8")
        content = response.content.decode("utf-8-sig")
        self.assertIn("Received,Name,Email", content)
        self.assertIn("'=HYPERLINK", content)  # neutralised formula
        self.assertNotIn("Rahim Uddin", content)

    def test_csv_export_of_selected_leads(self):
        response = self.client.post(reverse("dashboard:leads_bulk"), {"action": "export", "ids": [self.lead.pk]})
        self.assertIn("attachment;", response["Content-Disposition"])
        self.assertIn("Rahim Uddin", response.content.decode("utf-8-sig"))

    def test_leads_require_staff(self):
        self.client.logout()
        for url in (reverse("dashboard:leads_list"), self.lead.get_dashboard_url(), reverse("dashboard:leads_export")):
            self.assertEqual(self.client.get(url).status_code, 302)

    def test_dashboard_pipeline_summary(self):
        response = self.client.get(reverse("dashboard:index"))
        self.assertContains(response, "Lead pipeline")
        self.assertContains(response, "?lead_status=new")


class LeadEmailTests(TestCase):
    def setUp(self):
        cache.clear()  # reset the contact form's per-IP rate limit
        call_command("seed_content", verbosity=0)
        site = SiteSettings.load()
        site.email = "hello@thingbd.com"
        site.lead_notification_email = "sales@thingbd.com, boss@thingbd.com"
        site.save()

    def submit(self, **extra):
        data = {"name": "Rahim Uddin", "email": "rahim@example.com", "message": "Build us a site", "service": "Web Development", **extra}
        return self.client.post("/contact/", data, HTTP_ACCEPT="application/json", HTTP_REFERER="http://testserver/services/web-development/")

    def test_team_notification(self):
        self.assertEqual(self.submit().status_code, 200)
        self.assertEqual(len(mail.outbox), 1)  # auto-reply off by default
        email = mail.outbox[0]
        self.assertEqual(email.to, ["sales@thingbd.com", "boss@thingbd.com"])
        self.assertEqual(email.reply_to, ["rahim@example.com"])
        self.assertIn("Web Development", email.subject)
        self.assertIn("/dashboard/leads/", email.body)
        self.assertEqual(email.alternatives[0][1], "text/html")
        self.assertEqual(Lead.objects.get().page_url, "/services/web-development/")

    def test_autoreply_when_enabled(self):
        site = SiteSettings.load()
        site.send_lead_autoreply = True
        site.autoreply_message = "Hi {name}, thanks for asking about {service}. {unknown}"
        site.save()
        self.submit()
        reply = mail.outbox[1]
        self.assertEqual(reply.to, ["rahim@example.com"])
        self.assertIn("Hi Rahim, thanks for asking about Web Development. {unknown}", reply.body)

    def test_autoreply_does_not_echo_untrusted_service(self):
        site = SiteSettings.load()
        site.send_lead_autoreply = True
        site.autoreply_message = "About {service}"
        site.save()
        self.submit(service="Buy cheap pills at spam.example")
        self.assertIn("About your project", mail.outbox[1].body)

    def test_external_referer_not_stored(self):
        self.client.post("/contact/", {"name": "A", "email": "a@example.com", "message": "x"},
                         HTTP_ACCEPT="application/json", HTTP_REFERER="https://other.example/page")
        self.assertEqual(Lead.objects.get().page_url, "")

    def test_settings_validate_alert_addresses_and_autoreply(self):
        user = get_user_model().objects.create_user("ed", "ed@example.com", "Str0ng-pass!", is_staff=True)
        self.client.force_login(user)
        base = {"site_name": "Thingbd", "tagline": "YOUR VISION, OUR CODE", "contact_eyebrow": "x",
                "contact_title": "x", "contact_highlight": "x"}
        response = self.client.post(reverse("dashboard:site_settings"), {**base, "lead_notification_email": "ok@example.com, nope"})
        self.assertContains(response, "“nope” is not a valid email address.")
        response = self.client.post(reverse("dashboard:site_settings"), {**base, "send_lead_autoreply": "on", "autoreply_subject": ""})
        self.assertContains(response, "Required when the automatic reply is switched on.")
