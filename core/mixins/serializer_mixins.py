"""Reusable serializer mixins for common field patterns."""
from datetime import datetime

from django.conf import settings
from urllib.parse import urljoin


class ImageURLMixin:
    """Provides a ``get_image_url`` method that builds an absolute or relative URL
    depending on the ``IMAGE_URL_ABSOLUTE`` class attribute (default ``False``).
    """
    IMAGE_URL_ABSOLUTE = False

    def get_image_url(self, obj):
        if not obj.image:
            return None
        if self.IMAGE_URL_ABSOLUTE:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
            return urljoin(settings.SITE_URL, obj.image.url)
        return obj.image.url


class DateReceptionMixin:
    """Normalises ``date_reception`` to a date-only value."""

    def get_date_reception(self, obj):
        if isinstance(obj.date_reception, datetime):
            return obj.date_reception.date()
        return obj.date_reception


class UserFullNameMixin:
    """Provides ``get_user()`` returning 'nom prenom' or username as fallback."""

    def get_user(self, obj):
        try:
            nom = getattr(obj.user, 'nom', '') or ''
            prenom = getattr(obj.user, 'prenom', '') or ''
            full_name = f"{nom} {prenom}".strip()
            return full_name if full_name else getattr(obj.user, 'username', None)
        except Exception:
            return None
