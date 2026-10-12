from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm

from apps.core.models import SiteSettings, split_keywords


class ImageInput(forms.ClearableFileInput):
    """File input with a live preview of the current/selected image."""

    template_name = "dashboard/widgets/image_input.html"


class RichTextInput(forms.Textarea):
    """Textarea upgraded to a Quill rich-text editor by dashboard.js; stores HTML."""

    template_name = "dashboard/widgets/rich_text.html"


class KeywordsInput(forms.TextInput):
    """Comma-separated keywords, shown as removable chips by dashboard.js."""

    template_name = "dashboard/widgets/keywords.html"


class StyledFormMixin:
    """Adds the dashboard CSS classes to every widget."""

    rich_text_fields = ()  # TextFields edited with the rich-text editor

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name in self.rich_text_fields and not isinstance(field.widget, RichTextInput):
                field.widget = RichTextInput()
            if name == "meta_keywords" and not isinstance(field.widget, KeywordsInput):
                field.widget = KeywordsInput(attrs={"maxlength": field.max_length})
            widget = field.widget
            if isinstance(widget, forms.CheckboxSelectMultiple):
                css = "choice"
            elif isinstance(widget, forms.CheckboxInput):
                css = "switch"
            elif isinstance(widget, forms.ClearableFileInput):
                if isinstance(field, forms.ImageField) and not isinstance(widget, ImageInput):
                    field.widget = widget = ImageInput()
                css = "file-input"
            elif isinstance(widget, RichTextInput):
                css = "textarea richtext-source"
            elif isinstance(widget, forms.Textarea):
                css = "textarea"
                widget.attrs["rows"] = 3  # Django defaults to 10; users can drag to resize
            elif isinstance(widget, forms.Select):
                css = "select"
            else:
                css = "input"
            widget.attrs["class"] = f"{css} {widget.attrs.get('class', '')}".strip()

    def clean_meta_keywords(self):
        """Tidy keywords: trim, drop duplicates (any case), store as 'a, b, c'."""
        keywords = ", ".join(split_keywords(self.cleaned_data.get("meta_keywords", "")))
        max_length = self.fields["meta_keywords"].max_length
        if max_length and len(keywords) > max_length:
            raise forms.ValidationError(f"Too many keywords — keep the total under {max_length} characters.")
        return keywords


class FieldsetFormMixin:
    """Group fields into sections.

    `fieldsets` = [(title, icon, [field names]), ...] for the main column (or tabs),
    `side_fieldsets` = same shape, rendered in the narrow right-hand column.
    Fields not listed anywhere are appended to the first main section.
    """

    fieldsets = []
    side_fieldsets = []

    def _sections(self, spec, offset=0):
        return [
            {"title": title, "icon": icon, "slug": f"tab-{offset + i}", "fields": [self[name] for name in names]}
            for i, (title, icon, names) in enumerate(spec)
        ]

    def get_fieldsets(self):
        return self._sections(self.fieldsets)

    @property
    def main_sections(self):
        listed = {n for _, _, names in [*self.fieldsets, *self.side_fieldsets] for n in names}
        rest = [n for n in self.fields if n not in listed]
        spec = list(self.fieldsets) or [("Details", "edit_note", [])]
        if rest:
            title, icon, names = spec[0]
            spec[0] = (title, icon, [*names, *rest])
        return self._sections(spec)

    @property
    def side_sections(self):
        return self._sections(self.side_fieldsets, offset=100)


class LoginForm(StyledFormMixin, AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].widget.attrs.update({"placeholder": "Username", "autofocus": True})
        self.fields["password"].widget.attrs.update({"placeholder": "Password"})

    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        if not user.is_staff:
            raise forms.ValidationError("This account does not have dashboard access.", code="no_access")


class SiteSettingsForm(StyledFormMixin, FieldsetFormMixin, forms.ModelForm):
    fieldsets = [
        ("Brand", "palette", ["site_name", "tagline", "logo", "favicon", "footer_text"]),
        ("Contact info", "call", ["email", "phone", "whatsapp", "address"]),
        ("Social links", "share", ["facebook_url", "linkedin_url", "instagram_url", "x_url", "youtube_url", "github_url"]),
        ("Contact section", "forum", ["contact_eyebrow", "contact_title", "contact_highlight", "contact_text"]),
        ("Lead emails", "mark_email_unread", ["lead_notification_email", "send_lead_autoreply", "autoreply_subject", "autoreply_message"]),
        ("SEO & analytics", "travel_explore", ["meta_title", "meta_description", "meta_keywords", "og_image", "google_analytics_id"]),
    ]

    class Meta:
        model = SiteSettings
        fields = "__all__"
        labels = {"lead_notification_email": "Send new lead alerts to"}

    def clean_lead_notification_email(self):
        from django.core.validators import validate_email

        value = self.cleaned_data["lead_notification_email"]
        addresses = [a.strip() for a in value.replace(";", ",").split(",") if a.strip()]
        for address in addresses:
            try:
                validate_email(address)
            except forms.ValidationError:
                raise forms.ValidationError(f"“{address}” is not a valid email address.")
        return ", ".join(addresses)

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("send_lead_autoreply"):
            for name in ("autoreply_subject", "autoreply_message"):
                if not (cleaned.get(name) or "").strip():
                    self.add_error(name, "Required when the automatic reply is switched on.")
        return cleaned


class ProfileForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = get_user_model()
        fields = ("first_name", "last_name", "email")


class StyledPasswordChangeForm(StyledFormMixin, PasswordChangeForm):
    pass
