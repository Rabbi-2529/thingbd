"""Image uploads from the rich-text editor (blog posts, services, pages, ...)."""

import uuid

from django import forms
from django.core.files.storage import default_storage
from django.http import JsonResponse
from django.utils import timezone
from django.views import View

from .mixins import StaffRequiredMixin

MAX_UPLOAD_BYTES = 5 * 1024 * 1024
ALLOWED_FORMATS = {"JPEG": "jpg", "PNG": "png", "GIF": "gif", "WEBP": "webp"}


class EditorImageForm(forms.Form):
    image = forms.ImageField()  # Pillow verifies this really is an image

    def clean_image(self):
        image = self.cleaned_data["image"]
        if image.size > MAX_UPLOAD_BYTES:
            raise forms.ValidationError("Images must be 5 MB or smaller.")
        fmt = getattr(image.image, "format", None)
        if fmt not in ALLOWED_FORMATS:
            raise forms.ValidationError("Upload a JPG, PNG, GIF or WebP image.")
        image.ext = ALLOWED_FORMATS[fmt]
        return image


class EditorImageUploadView(StaffRequiredMixin, View):
    http_method_names = ["post"]

    def post(self, request):
        form = EditorImageForm(files=request.FILES)
        if not form.is_valid():
            return JsonResponse({"ok": False, "error": form.errors["image"][0]}, status=400)
        image = form.cleaned_data["image"]
        # Random file name: never trust the uploaded name or extension.
        path = f"uploads/{timezone.now():%Y/%m}/{uuid.uuid4().hex}.{image.ext}"
        saved = default_storage.save(path, image)
        return JsonResponse({"ok": True, "url": default_storage.url(saved)})
