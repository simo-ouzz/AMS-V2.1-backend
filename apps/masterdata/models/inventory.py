from django.utils import timezone
from django.db import models
from simple_history.models import HistoricalRecords

from core.mixins.auto_reference import AutoReferenceGeneratorMixin
from .user import UserWeb
from .master import operation, departement
from .location import emplacement
from .asset import item


class operation_article(models.Model):
    """Attachment and comments recorded on an item within an operation context."""
    item = models.ForeignKey(item, on_delete=models.CASCADE)
    operation = models.ForeignKey(operation, on_delete=models.CASCADE)
    prix = models.FloatField(blank=True,null=True)
    date_operation = models.DateField(blank=True,null=True)
    attachement = models.FileField(upload_to='attachmentsOperation/',blank=True,null=True)
    commentaire = models.TextField(blank=True,null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()
    def __str__(self):
        return f"{self.item} - {self.operation}"


class inventaire(AutoReferenceGeneratorMixin):
    REFERENCE_PREFIX = 'INV-'
    """Inventory campaign coordinating checks for multiple emplacements/items."""
    statut = [
        ("Terminer", "Terminer"),
        ('En attente', 'En attente'),
        ("En cours", "En cours"),
    ]
    categorie = [("Location","Location"),("Zone","Zone"),("Departement","Departement"),("Emplacement","Emplacement")]
    
    nom = models.CharField(max_length=250,unique=True)
    categorie = models.CharField(max_length=255, choices=categorie)
    reference = models.CharField(max_length=250,unique=True)
    user = models.ForeignKey(UserWeb, on_delete=models.CASCADE)
    statut = models.CharField(max_length=255, choices=statut ,default='En attente' )
    date_creation = models.DateTimeField()
    date_debut = models.DateTimeField(blank=True,null=True)
    date_fin = models.DateTimeField(blank=True,null=True)
    departement= models.ForeignKey(departement, on_delete=models.CASCADE,blank=True,null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()
    def __str__(self):
        return self.nom

    def lancer_inventaire(self, inventaire_id):
        inventaire_instance = inventaire.objects.get(id=inventaire_id)
        emplacements = inventaire_emplacement.objects.filter(inventaire=inventaire_instance)
        emplacement_en_cours = emplacements.filter(statut="En cours").count()
        if emplacement_en_cours >= 1:
            inventaire_instance.statut = "En cours"
            inventaire_instance.save()
        emplacements_terminer = emplacements.filter(statut="Terminer").count()
        if emplacements_terminer == emplacements.count():
            inventaire_instance.statut = "Terminer"
            inventaire_instance.date_fin = timezone.now()  
            inventaire_instance.save()
        return inventaire_instance



class inventaire_emplacement(models.Model):
    """Inventory state for a single emplacement within a campaign."""
    statut = [
        ("Terminer", "Terminer"),
        ("En attente", "En attente"),
        ("En cours", "En cours"),
        
    ]
    emplacement = models.ForeignKey(emplacement, on_delete=models.CASCADE)
    inventaire = models.ForeignKey(inventaire, on_delete=models.CASCADE)
    statut = models.CharField(max_length=255, choices=statut ,default="En attente")
    affceted_at = models.ForeignKey(UserWeb, on_delete=models.CASCADE, null=True, related_name='affected_at')
    start_at = models.BooleanField(default =False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()
    def __str__(self):
        return f"{self.emplacement} - {self.inventaire}"

class detail_inventaire(models.Model):
    """Inventory detail line linking an item and its observed state."""
    
    inventaire_emplacement = models.ForeignKey(inventaire_emplacement, on_delete=models.CASCADE, null=True,blank=True) 
    item = models.ForeignKey(item, on_delete=models.CASCADE, null=True, blank=True)
    tag_reference = models.CharField(max_length=255, null=True, blank=True)
    etat = models.CharField(
        max_length=255,
        choices=[
            ("trouvee", "trouvee"),
            ("intru", "intru"),
            ("manquant", "manquant"),
            ("inconnu", "inconnu"),
            ("non_affecter", "non_affecter"),
        ],
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()
    def __str__(self):
        item_label = self.item if self.item else (self.tag_reference or "No item")
        return f"{item_label} - {self.inventaire_emplacement}"
