"""A small, reusable CRUD engine for the dashboard.

Each content type is described once by a `CrudViewSet` subclass (see viewsets.py);
the views below turn that description into list / add / edit / delete screens,
drag-and-drop ordering, a visibility toggle and bulk actions.
"""

import json
from collections.abc import Callable
from dataclasses import dataclass
from urllib.parse import urlencode

from django.contrib import messages
from django.db import transaction
from django.db.models import Max, Q
from django.http import Http404, HttpResponse, HttpResponseBadRequest, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404
from django.urls import path, reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views import View
from django.views.generic import ListView, TemplateView

from .forms import RichTextInput
from .mixins import StaffRequiredMixin


@dataclass
class Column:
    field: str
    label: str = ""
    kind: str = "text"  # text | image | bool | badge | status | rating | date | muted
    primary: bool = False  # links to the edit screen


@dataclass
class ListFilter:
    """A dropdown filter in the list toolbar.

    `choices` is a list of (value, label) or a callable returning one;
    `apply(queryset, value)` returns the filtered queryset.
    """

    param: str
    label: str
    choices: object
    apply: Callable

    def get_choices(self):
        return list(self.choices() if callable(self.choices) else self.choices)


@dataclass
class BulkAction:
    """An extra bulk action: `handler(request, queryset)` returns a success message."""

    name: str
    label: str
    icon: str
    handler: Callable


class CrudViewSet:
    model = None
    form_class = None
    key = ""  # used for URL names (dashboard:<key>_list) and sidebar highlighting
    icon = "list"
    title = ""  # plural, e.g. "Services"
    title_singular = ""
    description = ""
    columns: list[Column] = []
    search_fields: list[str] = []
    active_field = "is_active"  # boolean field shown as a toggle; None to disable
    active_labels = ("Visible", "Hidden")
    sortable = True  # model has an `order` field
    paginate_by = 50
    formsets = []  # [(prefix, title, InlineFormSet class)]
    filters: list[ListFilter] = []
    bulk_actions: list[BulkAction] = []
    site_link_label = "View on website"
    delete_note = ""  # extra sentence on the delete confirmation page
    can_add = True  # False for records created elsewhere (e.g. leads from the contact form)
    public_path = ""  # e.g. "/services/__slug__/" for the Google preview in the editor
    empty_text = ""  # shown in the empty state when items cannot be added here

    def get_edit_url(self, obj):
        return self.url("edit", obj.pk)

    def get_header_links(self, request):
        """Extra buttons beside the page title: [(label, icon, url), ...]."""
        return []

    def before_save(self, request, obj, form, is_new):
        """Hook to adjust the object before it is saved (e.g. set the author)."""

    @property
    def noun(self):
        """Lower-case name for sentences ("Add service"), keeping acronyms ("Add FAQ")."""
        name = self.title_singular
        return name if name.isupper() else name.lower()

    # ---- URLs -------------------------------------------------------------
    def url(self, action, *args):
        return reverse(f"dashboard:{self.key}_{action}", args=args)

    def get_urls(self):
        k = self.key
        return [
            path(f"{k}/", CrudListView.as_view(viewset=self), name=f"{k}_list"),
            path(f"{k}/add/", CrudFormView.as_view(viewset=self), name=f"{k}_add"),
            path(f"{k}/<int:pk>/edit/", CrudFormView.as_view(viewset=self), name=f"{k}_edit"),
            path(f"{k}/<int:pk>/delete/", CrudDeleteView.as_view(viewset=self), name=f"{k}_delete"),
            path(f"{k}/<int:pk>/toggle/", CrudToggleView.as_view(viewset=self), name=f"{k}_toggle"),
            path(f"{k}/reorder/", CrudReorderView.as_view(viewset=self), name=f"{k}_reorder"),
            path(f"{k}/bulk/", CrudBulkView.as_view(viewset=self), name=f"{k}_bulk"),
        ]

    # ---- Data -------------------------------------------------------------
    def get_queryset(self):
        return self.model.objects.all()

    def build_row(self, obj):
        cells = []
        for col in self.columns:
            value = getattr(obj, col.field)
            if col.kind == "badge":
                value = getattr(obj, f"get_{col.field}_display")()
            elif col.kind == "image":
                value = value.url if value else None
            elif callable(value):
                value = value()
            cells.append({"col": col, "value": value})
        return {
            "obj": obj,
            "cells": cells,
            "edit_url": self.get_edit_url(obj),
            "delete_url": self.url("delete", obj.pk),
            "toggle_url": self.url("toggle", obj.pk) if self.active_field else None,
            "active": getattr(obj, self.active_field) if self.active_field else None,
            "site_url": obj.get_absolute_url() if hasattr(obj, "get_absolute_url") else None,
        }


class ViewSetMixin(StaffRequiredMixin):
    viewset: CrudViewSet = None

    @property
    def active_nav(self):
        return self.viewset.key

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["vs"] = self.viewset
        context["list_url"] = self.viewset.url("list")
        return context


def _safe_redirect(request, fallback):
    nxt = request.POST.get("next") or request.GET.get("next")
    if nxt and url_has_allowed_host_and_scheme(nxt, allowed_hosts={request.get_host()}):
        return nxt
    return fallback


class CrudListView(ViewSetMixin, ListView):
    template_name = "dashboard/crud/list.html"

    @property
    def page_title(self):
        return self.viewset.title

    def get_paginate_by(self, queryset):
        return self.viewset.paginate_by

    def get_queryset(self):
        vs = self.viewset
        qs = vs.get_queryset()
        self.q = self.request.GET.get("q", "").strip()
        self.status = self.request.GET.get("status", "")
        if self.q and vs.search_fields:
            cond = Q()
            for field in vs.search_fields:
                cond |= Q(**{f"{field}__icontains": self.q})
            qs = qs.filter(cond)
        if vs.active_field and self.status in ("on", "off"):
            qs = qs.filter(**{vs.active_field: self.status == "on"})
        self.filter_values = {}
        for flt in vs.filters:
            value = self.request.GET.get(flt.param, "")
            if value and value in {str(v) for v, _ in flt.get_choices()}:
                self.filter_values[flt.param] = value
                qs = flt.apply(qs, value)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        vs = self.viewset
        page = context.get("page_obj")
        filtered = bool(self.q or self.status or self.filter_values)
        params = {k: v for k, v in self.request.GET.items() if k != "page" and v}
        context.update(
            rows=[vs.build_row(obj) for obj in context["object_list"]],
            q=self.q,
            status=self.status,
            filtered=filtered,
            filters=[
                {"param": f.param, "label": f.label, "choices": f.get_choices(), "value": self.filter_values.get(f.param, "")}
                for f in vs.filters
            ],
            page_query=urlencode(params),
            total=vs.get_queryset().count(),
            can_drag=vs.sortable and not filtered and not (page and page.paginator.num_pages > 1),
            current_url=self.request.get_full_path(),
            add_url=vs.url("add") if vs.can_add else None,
            header_links=vs.get_header_links(self.request),
            bulk_url=vs.url("bulk"),
            reorder_url=vs.url("reorder"),
        )
        return context


class CrudFormView(ViewSetMixin, TemplateView):
    template_name = "dashboard/crud/form.html"

    def dispatch(self, request, *args, **kwargs):
        pk = kwargs.get("pk")
        if self.viewset.form_class is None or (pk is None and not self.viewset.can_add):
            raise Http404("This item cannot be added or edited here.")
        self.object = get_object_or_404(self.viewset.get_queryset(), pk=pk) if pk else None
        return super().dispatch(request, *args, **kwargs)

    @property
    def page_title(self):
        vs = self.viewset
        return f"Edit {vs.noun}" if self.object else f"Add {vs.noun}"

    def build_forms(self, data=None, files=None):
        form = self.viewset.form_class(data, files, instance=self.object)
        formsets = [
            {"prefix": prefix, "title": title, "formset": cls(data, files, instance=self.object, prefix=prefix)}
            for prefix, title, cls in self.viewset.formsets
        ]
        return form, formsets

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if "form" not in context:
            context["form"], context["formsets"] = self.build_forms()
        context["object"] = self.object
        context["site_url"] = self.object.get_absolute_url() if self.object and hasattr(self.object, "get_absolute_url") else None
        context["delete_url"] = self.viewset.url("delete", self.object.pk) if self.object else None
        context["has_richtext"] = any(isinstance(f.widget, RichTextInput) for f in context["form"].fields.values())
        return context

    def post(self, request, *args, **kwargs):
        vs = self.viewset
        form, formsets = self.build_forms(request.POST, request.FILES)
        if not (form.is_valid() and all(fs["formset"].is_valid() for fs in formsets)):
            messages.error(request, "Please fix the highlighted fields.")
            return self.render_to_response(self.get_context_data(form=form, formsets=formsets))

        is_new = self.object is None
        with transaction.atomic():
            obj = form.save(commit=False)
            if is_new and vs.sortable:
                obj.order = (vs.model.objects.aggregate(m=Max("order"))["m"] or 0) + 1
            vs.before_save(request, obj, form, is_new)
            obj.save()
            form.save_m2m()
            for fs in formsets:
                fs["formset"].instance = obj
                fs["formset"].save()

        messages.success(request, f"{vs.title_singular} “{obj}” {'added' if is_new else 'saved'}.")
        if "_continue" in request.POST:
            return HttpResponseRedirect(vs.url("edit", obj.pk))
        if "_addanother" in request.POST:
            return HttpResponseRedirect(vs.url("add"))
        return HttpResponseRedirect(vs.url("list"))


class CrudDeleteView(ViewSetMixin, TemplateView):
    template_name = "dashboard/crud/confirm_delete.html"

    def dispatch(self, request, *args, **kwargs):
        self.object = get_object_or_404(self.viewset.get_queryset(), pk=kwargs["pk"])
        return super().dispatch(request, *args, **kwargs)

    @property
    def page_title(self):
        return f"Delete {self.viewset.noun}"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["object"] = self.object
        context["edit_url"] = self.viewset.get_edit_url(self.object)
        return context

    def post(self, request, *args, **kwargs):
        name = str(self.object)
        self.object.delete()
        messages.success(request, f"{self.viewset.title_singular} “{name}” deleted.")
        return HttpResponseRedirect(self.viewset.url("list"))


class CrudToggleView(ViewSetMixin, View):
    http_method_names = ["post"]

    def post(self, request, pk):
        vs = self.viewset
        if not vs.active_field:
            return HttpResponseBadRequest()
        obj = get_object_or_404(vs.get_queryset(), pk=pk)
        new_value = not getattr(obj, vs.active_field)
        setattr(obj, vs.active_field, new_value)
        obj.save(update_fields=[vs.active_field])
        if request.headers.get("Accept", "").startswith("application/json"):
            return JsonResponse({"ok": True, "active": new_value})
        return HttpResponseRedirect(_safe_redirect(request, vs.url("list")))


class CrudReorderView(ViewSetMixin, View):
    http_method_names = ["post"]

    def post(self, request):
        vs = self.viewset
        try:
            ids = [int(i) for i in json.loads(request.body)["ids"]]
        except (ValueError, KeyError, TypeError):
            return HttpResponseBadRequest("Expected {\"ids\": [...]}")
        objects = {o.pk: o for o in vs.get_queryset().filter(pk__in=ids)}
        updated = []
        for index, pk in enumerate(ids, start=1):
            if pk in objects:
                objects[pk].order = index
                updated.append(objects[pk])
        vs.model.objects.bulk_update(updated, ["order"])
        return JsonResponse({"ok": True, "count": len(updated)})


class CrudBulkView(ViewSetMixin, View):
    http_method_names = ["post"]

    def post(self, request):
        vs = self.viewset
        action = request.POST.get("action")
        ids = request.POST.getlist("ids")
        qs = vs.get_queryset().filter(pk__in=[i for i in ids if i.isdigit()])
        count = qs.count()
        if not count:
            messages.warning(request, "Select at least one item first.")
        elif action == "delete":
            for obj in qs:  # per-object delete so model delete() hooks run
                obj.delete()
            messages.success(request, f"Deleted {count} item(s).")
        elif action in ("show", "hide") and vs.active_field:
            qs.update(**{vs.active_field: action == "show"})
            label = vs.active_labels[0] if action == "show" else vs.active_labels[1]
            messages.success(request, f"{count} item(s) set to {label.lower()}.")
        elif custom := next((a for a in vs.bulk_actions if a.name == action), None):
            result = custom.handler(request, qs)
            if isinstance(result, HttpResponse):  # e.g. a CSV download
                return result
            messages.success(request, result)
        else:
            messages.error(request, "Unknown action.")
        return HttpResponseRedirect(_safe_redirect(request, vs.url("list")))
