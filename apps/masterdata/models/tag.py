from django.db import models
from simple_history.models import HistoricalRecords

from .user import Compte, UserWeb
from .master import type_tag
from .location import emplacement
from .asset import item


class tag(models.Model):
    """RFID/Barcode tag assigned to items."""
    statut = [
        ('on', 'on'),
        ('off', 'off'),
        
    ]
    reference = models.CharField(max_length = 250,unique=True)
    statut = models.CharField(choices=statut ,max_length = 250,default='on')
    affecter = models.BooleanField(default = False)
    type = models.ForeignKey(type_tag, on_delete=models.CASCADE, blank=True, null=True)
    compte = models.ForeignKey(Compte,on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()
    def __str__(self):
        return self.reference
    
    

class tagEmplacement(models.Model):
    """Tag assigned to locations/emplacements for scanning and audits."""
    statut = [
        ('on', 'on'),
        ('off', 'off'),
        
    ]
    reference = models.CharField(max_length = 250,unique=True)
    statut = models.CharField(choices=statut ,max_length = 250,default='on')
    affecter = models.BooleanField(default = False)
    type = models.ForeignKey(type_tag, on_delete=models.CASCADE, blank=True, null=True)
    compte = models.ForeignKey(Compte,on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()
    def __str__(self):
        return self.reference


class TagHistory(models.Model):
    """Audit trail for tag changes on items (who changed what and when)."""
    item = models.ForeignKey(item, on_delete=models.CASCADE, related_name='tag_history')
    old_tag = models.ForeignKey(tag, on_delete=models.CASCADE, null=True, related_name='old_tag')
    new_tag = models.ForeignKey(tag, on_delete=models.CASCADE, null=True, related_name='new_tag')
    changed_by = models.ForeignKey(UserWeb, on_delete=models.CASCADE, null=True, related_name='user_changed')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()

    def __str__(self):
        return f"Item: {self.item.reference_auto}, Ancien Tag: {self.old_tag.reference if self.old_tag else 'None'}, Nouveau Tag: {self.new_tag.reference if self.new_tag else 'None'}"


class TagHistoryEmplacement(models.Model):
    """Audit trail for tag changes on locations (emplacements)."""
    emplacement = models.ForeignKey(emplacement, on_delete=models.CASCADE, related_name='tag_history_emplacement')
    old_tag = models.ForeignKey(tagEmplacement, on_delete=models.CASCADE, null=True, related_name='old_tag')
    new_tag = models.ForeignKey(tagEmplacement, on_delete=models.CASCADE, null=True, related_name='new_tag')
    changed_by = models.ForeignKey(UserWeb, on_delete=models.CASCADE, null=True, related_name='user_change')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()

    def __str__(self):
        return f"emplacement: {self.emplacement.nom}, Ancien Tag: {self.old_tag.reference if self.old_tag else 'None'}, Nouveau Tag: {self.new_tag.reference if self.new_tag else 'None'}"
