from django.db import models
from simple_history.models import HistoricalRecords

from core.mixins.auto_reference import AutoReferenceGeneratorMixin
from .user import Compte


class location(AutoReferenceGeneratorMixin):
    REFERENCE_PREFIX = 'LOC-'
    """Physical site/location (e.g., building/campus)."""
    nom = models.CharField(max_length = 250,unique=True)
    reference = models.CharField(max_length = 250,unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    compte = models.ForeignKey(Compte,on_delete=models.CASCADE)
    history = HistoricalRecords()
    class Meta:
        verbose_name = " Local"
    def __str__(self):
        return self.nom


class zone(AutoReferenceGeneratorMixin):
    REFERENCE_PREFIX = 'ZONE-'
    """Area within a location (e.g., floor/wing)."""
    nom = models.CharField(max_length = 250,unique=True)
    location = models.ForeignKey(location, on_delete=models.CASCADE)
    reference = models.CharField(max_length = 250,unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()
    def __str__(self):
        return self.nom


class emplacement(AutoReferenceGeneratorMixin):
    REFERENCE_PREFIX = 'EMP-'
    """Precise place to store or assign items (e.g., room/shelf)."""
    nom = models.CharField(max_length = 250,unique=True)
    zone = models.ForeignKey(zone, on_delete=models.CASCADE)
    reference = models.CharField(max_length = 250,unique=True)
    tag = models.ForeignKey('masterdata.tagEmplacement', on_delete=models.SET_NULL, blank=True, null=True, related_name='emplacements')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()
    def __str__(self):
        return self.nom
