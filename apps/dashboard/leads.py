"""Leads inbox (Phase 4): list, detail page with status pipeline and notes, CSV export."""

import csv

from django import forms
from django.contrib import messages
from django.db.models import Count
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.views.generic import TemplateView

from apps.leads.models import Lead, LeadNote

from .crud import BulkAction, Column, CrudListView, CrudViewSet, ListFilter
from .forms import StyledFormMixin
from .mixins import StaffRequiredMixin

CSV_FIELDS = [
    ("created_at", "Received"), ("name", "Name"), ("email", "Email"), ("phone", "Phone"),
    ("company", "Company"), ("service", "Service"), ("budget", "Budget"),
    ("status", "Status"), ("message", "Message"), ("page_url", "Sent from"),
]


def _csv_safe(value):
    """Stop spreadsheet apps from treating visitor text as a formula (CSV injection)."""
    text = "" if value is None else str(value)
    return "'" + text if text[:1] in ("=", "+", "-", "@", "\t", "\r") else text


def leads_csv_response(queryset):
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="thingbd-leads-{timezone.localdate():%Y-%m-%d}.csv"'
    response.write("﻿")  # BOM so Excel opens UTF-8 (e.g. Bangla names) correctly
    writer = csv.writer(response)
    writer.writerow([label for _, label in CSV_FIELDS])
    for lead in queryset:
        row = []
        for field, _ in CSV_FIELDS:
            if field == "created_at":
                row.append(timezone.localtime(lead.created_at).strftime("%Y-%m-%d %H:%M"))
            elif field == "status":
                row.append(lead.get_status_display())
            else:
                row.append(_csv_safe(getattr(lead, field)))
        writer.writerow(row)
    return response


def _set_status(status):
    def handler(request, qs):
        changed = sum(1 for lead in qs if lead.set_status(status, request.user))
        return f"{changed} lead(s) marked as {Lead.Status(status).label.lower()}."
    return handler


class LeadViewSet(CrudViewSet):
    model = Lead
    form_class = None
    key, icon = "leads", "inbox"
    title, title_singular = "Leads", "Lead"
    description = "Enquiries from the website contact form."
    empty_text = "When someone fills in the contact form on the website, their enquiry will appear here."
    can_add = False
    active_field = None
    sortable = False
    paginate_by = 30
    columns = [
        Column("name", "Name", primary=True),
        Column("email", "Email", kind="muted"),
        Column("company", "Company", kind="muted"),
        Column("service", "Service", kind="muted"),
        Column("status_badge", "Status", kind="status"),
        Column("created_at", "Received", kind="ago"),
    ]
    search_fields = ["name", "email", "company", "phone", "message"]
    filters = [
        ListFilter("lead_status", "Status", Lead.Status.choices, lambda qs, v: qs.filter(status=v)),
        ListFilter("service", "Service",
                   lambda: [(s, s) for s in Lead.objects.exclude(service="").order_by("service").values_list("service", flat=True).distinct()],
                   lambda qs, v: qs.filter(service=v)),
    ]
    bulk_actions = [
        BulkAction("mark_contacted", "Contacted", "call_made", _set_status(Lead.Status.CONTACTED)),
        BulkAction("mark_won", "Won", "emoji_events", _set_status(Lead.Status.WON)),
        BulkAction("mark_lost", "Lost", "block", _set_status(Lead.Status.LOST)),
        BulkAction("export", "Export CSV", "download", lambda request, qs: leads_csv_response(qs)),
    ]

    def get_edit_url(self, obj):
        return reverse("dashboard:lead_detail", args=[obj.pk])

    def get_header_links(self, request):
        query = request.GET.urlencode()
        return [("Export CSV", "download", reverse("dashboard:leads_export") + (f"?{query}" if query else ""))]


LEADS = LeadViewSet()


class LeadExportView(CrudListView):
    """Exports every lead matching the current search and filters (not just one page)."""

    viewset = LEADS

    def get(self, request, *args, **kwargs):
        return leads_csv_response(self.get_queryset())


class NoteForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = LeadNote
        fields = ("text",)
        widgets = {"text": forms.Textarea(attrs={"placeholder": "Add a note: call summary, next step, quote sent…"})}
        labels = {"text": "New note"}


class LeadDetailView(StaffRequiredMixin, TemplateView):
    template_name = "dashboard/leads/detail.html"
    active_nav = "leads"

    def dispatch(self, request, *args, **kwargs):
        self.lead = get_object_or_404(Lead, pk=kwargs["pk"])
        return super().dispatch(request, *args, **kwargs)

    @property
    def page_title(self):
        return self.lead.name

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        lead = self.lead
        statuses = list(Lead.Status)
        current = statuses.index(Lead.Status(lead.status))
        context.update(
            lead=lead,
            vs=LEADS,
            list_url=LEADS.url("list"),
            note_form=kwargs.get("note_form") or NoteForm(),
            timeline=lead.notes.select_related("author"),
            pipeline=[
                {"value": s.value, "label": s.label, "current": i == current,
                 "done": i < current and lead.status not in (Lead.Status.LOST,)}
                for i, s in enumerate(statuses)
            ],
            other_leads=Lead.objects.filter(email__iexact=lead.email).exclude(pk=lead.pk)[:5],
            newer=Lead.objects.filter(created_at__gt=lead.created_at).order_by("created_at").first(),
            older=Lead.objects.filter(created_at__lt=lead.created_at).order_by("-created_at").first(),
        )
        return context

    def post(self, request, *args, **kwargs):
        lead = self.lead
        action = request.POST.get("action")
        if action == "status":
            if lead.set_status(request.POST.get("status", ""), request.user):
                messages.success(request, f"Status changed to {lead.get_status_display()}.")
        elif action == "note":
            form = NoteForm(request.POST)
            if not form.is_valid():
                return self.render_to_response(self.get_context_data(note_form=form))
            note = form.save(commit=False)
            note.lead, note.author = lead, request.user
            note.save()
            messages.success(request, "Note added.")
        elif action == "delete_note":
            note = get_object_or_404(LeadNote, pk=request.POST.get("note"), lead=lead, kind=LeadNote.Kind.NOTE)
            if note.author_id in (None, request.user.pk) or request.user.is_superuser:
                note.delete()
                messages.success(request, "Note deleted.")
            else:
                messages.error(request, "You can only delete your own notes.")
        return HttpResponseRedirect(lead.get_dashboard_url())


def lead_pipeline_summary():
    """Counts per status for the dashboard home."""
    counts = dict(Lead.objects.values_list("status").annotate(n=Count("pk")))
    total = sum(counts.values()) or 1
    return [
        {"value": s.value, "label": s.label, "count": counts.get(s.value, 0), "pct": round(100 * counts.get(s.value, 0) / total)}
        for s in Lead.Status
    ]
