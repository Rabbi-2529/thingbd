from django import forms

from .models import Lead


class LeadForm(forms.ModelForm):
    # Honeypot: hidden from people, bots tend to fill it in.
    website = forms.CharField(required=False, widget=forms.TextInput(attrs={"tabindex": "-1", "autocomplete": "off"}))

    class Meta:
        model = Lead
        fields = ("name", "email", "phone", "company", "service", "budget", "message")

    def clean_website(self):
        if self.cleaned_data.get("website"):
            raise forms.ValidationError("Spam detected.")
        return ""
