from django.conf import settings
from django.db import models
from django.urls import reverse


class Lead(models.Model):
    class Status(models.TextChoices):
        NEW = "new", "New"
        CONTACTED = "contacted", "Contacted"
        PROPOSAL = "proposal", "Proposal sent"
        WON = "won", "Won"
        LOST = "lost", "Lost"

    name = models.CharField(max_length=120)
    email = models.EmailField()
    phone = models.CharField(max_length=40, blank=True)
    company = models.CharField(max_length=120, blank=True)
    service = models.CharField(max_length=120, blank=True)
    budget = models.CharField(max_length=40, blank=True)
    message = models.TextField(max_length=4000)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.NEW, db_index=True)
    page_url = models.CharField("Sent from page", max_length=255, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} <{self.email}>"

    def get_dashboard_url(self):
        return reverse("dashboard:lead_detail", args=[self.pk])

    @property
    def status_badge(self):
        return self.status, self.get_status_display()

    @property
    def whatsapp_number(self):
        digits = "".join(ch for ch in self.phone if ch.isdigit())
        return digits if len(digits) >= 8 else ""

    def set_status(self, new_status, user=None):
        """Change status and record it in the activity timeline. Returns True if it changed."""
        if new_status == self.status or new_status not in self.Status.values:
            return False
        old_label = self.get_status_display()
        self.status = new_status
        self.save(update_fields=["status", "updated_at"])
        LeadNote.objects.create(
            lead=self, author=user, kind=LeadNote.Kind.STATUS,
            text=f"Status changed from {old_label} to {self.get_status_display()}",
        )
        return True


class LeadNote(models.Model):
    class Kind(models.TextChoices):
        NOTE = "note", "Note"
        STATUS = "status", "Status change"

    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name="notes")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    kind = models.CharField(max_length=10, choices=Kind.choices, default=Kind.NOTE)
    text = models.TextField(max_length=4000)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return self.text[:60]
