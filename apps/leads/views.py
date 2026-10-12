from urllib.parse import urlparse

from django.contrib import messages
from django.core.cache import cache
from django.http import JsonResponse
from django.shortcuts import redirect
from django.views.decorators.http import require_POST

from .forms import LeadForm
from .notifications import notify_team, send_autoreply

RATE_LIMIT = 5  # submissions per IP per hour


def _client_ip(request):
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    return forwarded.split(",")[0].strip() if forwarded else request.META.get("REMOTE_ADDR")


def _source_page(request):
    """Path of the page the form was sent from (same-site referers only)."""
    referer = urlparse(request.META.get("HTTP_REFERER", ""))
    if referer.netloc and referer.netloc != request.get_host():
        return ""
    return (referer.path or "")[:255]


@require_POST
def contact_submit(request):
    wants_json = request.headers.get("Accept", "").startswith("application/json")
    ip = _client_ip(request)
    key = f"lead-rate:{ip}"
    if cache.get(key, 0) >= RATE_LIMIT:
        error = "Too many submissions. Please try again later."
        if wants_json:
            return JsonResponse({"ok": False, "errors": {"__all__": [error]}}, status=429)
        messages.error(request, error)
        return redirect("/#contact")

    form = LeadForm(request.POST)
    if not form.is_valid():
        if wants_json:
            return JsonResponse({"ok": False, "errors": form.errors}, status=422)
        messages.error(request, "Please check the form and try again.")
        return redirect("/#contact")

    lead = form.save(commit=False)
    lead.ip_address = ip
    lead.page_url = _source_page(request)
    lead.save()
    cache.set(key, cache.get(key, 0) + 1, 3600)
    notify_team(lead, request)
    send_autoreply(lead)

    if wants_json:
        return JsonResponse({"ok": True})
    messages.success(request, "Thanks. We will contact you within one business day.")
    return redirect("/#contact")
