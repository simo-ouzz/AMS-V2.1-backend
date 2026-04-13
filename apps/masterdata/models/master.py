from django.db import models
from simple_history.models import HistoricalRecords

from core.mixins.auto_reference import AutoReferenceGeneratorMixin
from .user import Compte


class Personne(AutoReferenceGeneratorMixin):
    REFERENCE_PREFIX = 'PRSN-'
    """Physical person to which items can be assigned (affectation)."""
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
    ]
    
    prenom = models.CharField(max_length=100)
    nom = models.CharField(max_length=100)
    reference = models.CharField(max_length = 255,unique=True)
    compte = models.ForeignKey(Compte, on_delete=models.CASCADE)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.prenom} {self.nom}"


class categorie(AutoReferenceGeneratorMixin):
    REFERENCE_PREFIX = 'CAT-'
    """Product family category (e.g., IT, Vehicles, Furniture)."""
    libelle = models.CharField(max_length = 255,unique=True)
    reference = models.CharField(max_length = 255,unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()
    def __str__(self):
        return self.libelle
    

class produit(AutoReferenceGeneratorMixin):
    REFERENCE_PREFIX = 'PRD-'
    REFERENCE_FIELD = 'code_produit'
    """Product family (template) with amortization duration and management mode."""
    type = [
        ('en masse', 'en masse'),
        ('individuellement', 'individuellement'),
        
    ]
    libelle = models.CharField(max_length = 255,unique=True)
    code_produit = models.CharField(max_length = 255, verbose_name="Reference",unique=True)
    categorie = models.ForeignKey(categorie, on_delete=models.CASCADE)
    duree_amourtissement = models.IntegerField(default=3, verbose_name="Durée d'amortissement")
    statut = models.CharField(choices=type ,max_length = 250)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()
    class Meta:
        verbose_name = " Famille"
    def __str__(self):
        return self.libelle


class nature(AutoReferenceGeneratorMixin):
    REFERENCE_PREFIX = 'NTR-'
    """Domain-specific nature of an article (custom taxonomy)."""
    libelle = models.CharField(max_length = 255,unique=True)
    reference = models.CharField(max_length = 255,unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()
    def __str__(self):
        return self.libelle


class fournisseur(AutoReferenceGeneratorMixin):
    REFERENCE_PREFIX = 'FRN-'
    """Supplier providing articles/assets."""
    nom = models.CharField(max_length=250)
    reference = models.CharField(max_length=250, unique=True)  
    ice = models.CharField(max_length=250, default="Null")
    tel = models.CharField(max_length=50, default="Null")
    adresse = models.CharField(max_length=250,default="Null")
    compte = models.ForeignKey(Compte, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()

    def __str__(self):
        return f"{self.nom}"

class operation(models.Model):
    """Operation reference to attach files/comments on items."""
    reference = models.CharField(max_length = 250,unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()
    def __str__(self):
        return self.reference


class departement(AutoReferenceGeneratorMixin):
    REFERENCE_PREFIX = 'DPR-'
    """Organizational department owning or using items."""
    nom = models.CharField(max_length = 255,unique=True)
    reference = models.CharField(max_length = 255,unique=True)
    compte = models.ForeignKey(Compte,on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True) 
    history = HistoricalRecords()
    def __str__(self):
        return self.nom  


class marque(models.Model):
    """Brand of article or equipment."""
    nom = models.CharField(max_length = 250,unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()
    def __str__(self):
        return self.nom

class type_tag(models.Model):
    """Type of tags used for items or locations."""
    nom = models.CharField(max_length = 250,unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()
    def __str__(self):
        return self.nom


class Fichier(models.Model):
    """Metadata for imported files (size, number of rows)."""
    nom = models.CharField(max_length=255,unique=True)
    taille = models.PositiveIntegerField()
    nombre_lignes = models.PositiveIntegerField()
    
    history = HistoricalRecords()
    def __str__(self):
        return f"{self.nom} - {self.taille} octets - {self.nombre_lignes} lignes"
