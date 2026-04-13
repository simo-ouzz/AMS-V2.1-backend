"""AutoReferenceGeneratorMixin — eliminates duplicate save() blocks across models.

Each model that needs an auto-generated reference must declare two class attributes:

    REFERENCE_FIELD  — name of the CharField that holds the reference (default: 'reference')
    REFERENCE_PREFIX — the prefix string, e.g. 'PRSN-', 'CAT-', 'LOC-'

Example::

    class Personne(AutoReferenceGeneratorMixin, models.Model):
        REFERENCE_PREFIX = 'PRSN-'
        reference = models.CharField(max_length=255, unique=True)
        ...

The mixin reads the highest existing reference from the DB, extracts the
trailing integer, increments it, and zero-pads it to 6 digits.
"""
import re

from django.db import models


class AutoReferenceGeneratorMixin(models.Model):
    """Mixin that auto-generates a sequential prefixed reference on first save.

    Subclasses MUST define:
        REFERENCE_PREFIX (str)   — e.g. ``'PRSN-'``
        REFERENCE_FIELD  (str)   — name of the reference field (default ``'reference'``)
    """

    REFERENCE_PREFIX: str = ""
    REFERENCE_FIELD: str = "reference"

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        field_name = self.__class__.REFERENCE_FIELD
        prefix = self.__class__.REFERENCE_PREFIX

        if prefix and not getattr(self, field_name):
            escaped = re.escape(prefix)
            last_ref = (
                self.__class__.objects
                .filter(**{f"{field_name}__startswith": prefix})
                .order_by(f"-{field_name}")
                .values_list(field_name, flat=True)
                .first()
            )
            next_number = 1
            if last_ref:
                match = re.search(rf"{escaped}(\d+)", last_ref)
                if match:
                    next_number = int(match.group(1)) + 1

            setattr(self, field_name, f"{prefix}{next_number:06d}")

        super().save(*args, **kwargs)
