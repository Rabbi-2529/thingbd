"""Emails sent when a lead arrives: a notification to the team and an optional auto-reply."""

import logging

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.mail import EmailMultiAlternatives
from django.core.validators import validate_email
from django.template.loader import render_to_string

from apps.core.models import SiteSettings

logger = logging.getLogger(__name__)


def parse_recipients(value):
    """Split a comma/semicolon separated list into valid addresses."""
    recipients = []
    for part in value.replace(";", ",").split(","):
        part = part.strip()
        if not part:
            continue
        try:
            validate_email(part)
        except ValidationError:
            logger.warning("Skipping invalid lead notification address: %s", part)
            continue
        recipients.append(part)
    return recipients


def _send(subject, template, context, to, reply_to=None):
    text = render_to_string(f"emails/{template}.txt", context)
    html = render_to_string(f"emails/{template}.html", context)
    message = EmailMultiAlternatives(subject, text, settings.DEFAULT_FROM_EMAIL, to, reply_to=reply_to)
    message.attach_alternative(html, "text/html")
    message.send()


def notify_team(lead, request=None):
    site = SiteSettings.load()
    recipients = parse_recipients(site.lead_notification_email or site.email)
    if not recipients:
        return False
    dashboard_url = lead.get_dashboard_url()
    if request is not None:
        dashboard_url = request.build_absolute_uri(dashboard_url)
    context = {"lead": lead, "site": site, "dashboard_url": dashboard_url}
    try:
        _send(f"New lead: {lead.name}" + (f" — {lead.service}" if lead.service else ""),
              "lead_notification", context, recipients, reply_to=[lead.email])
        return True
    except Exception:
        logger.exception("Could not send lead notification email")
        return False


class _SafeFormat(dict):
    def __missing__(self, key):
        return "{" + key + "}"


def send_autoreply(lead):
    site = SiteSettings.load()
    if not site.send_lead_autoreply:
        return False
    # The auto-reply goes to whatever address the visitor typed, so keep visitor-supplied text
    # to a minimum (first name only, known service names only) to avoid being used as a spam relay.
    from apps.website.models import Service

    first_name = (lead.name.split() or [""])[0][:30]
    known = set(Service.objects.filter(is_active=True).values_list("title", flat=True))
    service = lead.service if lead.service in known else "your project"
    values = _SafeFormat(name=first_name, service=service)
    body = site.autoreply_message.format_map(values)
    reply_to = parse_recipients(site.email)
    try:
        _send(site.autoreply_subject, "lead_autoreply", {"body": body, "site": site, "lead": lead},
              [lead.email], reply_to=reply_to or None)
        return True
    except Exception:
        logger.exception("Could not send lead auto-reply")
        return False
