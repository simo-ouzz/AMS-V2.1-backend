import re
from datetime import datetime

from django.db import models
from simple_history.models import HistoricalRecords

from core.mixins.auto_reference import AutoReferenceGeneratorMixin
from .user import Compte
from .master import Personne, produit, marque, fournisseur, nature, departement, Fichier
from .location import emplacement


class article(AutoReferenceGeneratorMixin):
    REFERENCE_PREFIX = 'ARTL-'
    REFERENCE_FIELD = 'code_article'
    """Purchased article (acquisition). Can generate one or more concrete items."""
    
    code_article = models.CharField(max_length = 250,unique=False,blank=True,null=True)
    designation = models.CharField(max_length = 250,unique=False)
    date_achat = models.DateField()
    numero_comptable = models.CharField(max_length = 250,blank=True,null=True)
    image = models.ImageField(upload_to='_images_articles/',blank=True,null=True)
    couleur = models.CharField(max_length = 100,blank=True,null=True)
    poids = models.FloatField(blank=True,null=True)
    volume = models.FloatField(blank=True,null=True)
    langueur = models.FloatField(blank=True,null=True)
    hauteur= models.FloatField(blank=True,null=True)
    largeur = models.FloatField(blank=True,null=True)
    date_expiration = models.DateField(blank=True,null=True)
    date_peremption = models.DateField(blank=True,null=True)
    date_reception = models.DateTimeField(auto_now_add=True)
    prix_achat = models.FloatField(default=0)
    attachement1 = models.FileField(blank=True,null=True,upload_to='_fichier_article/')
    attachement2 = models.FileField(blank=True,null=True,upload_to='_fichier_article/')
    attachement3 = models.FileField(blank=True,null=True,upload_to='_fichier_article/')
    qte = models.IntegerField(default=1,null=True)
    qte_recue = models.IntegerField(blank=True,null=True)
    N_facture = models.CharField(max_length=255)
    valider = models.BooleanField(default = True)
    via_erp = models.BooleanField(default = False,blank=True,null=True)
    compte = models.ForeignKey(Compte, on_delete=models.CASCADE)
    produit = models.ForeignKey(produit, on_delete=models.CASCADE)
    marque = models.ForeignKey(marque, on_delete=models.CASCADE,blank=True,null=True)
    fournisseur = models.ForeignKey(fournisseur, on_delete=models.CASCADE,blank=True,null=True)
    nature = models.ForeignKey(nature, on_delete=models.CASCADE,blank=True,null=True)    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    fichier = models.ForeignKey(Fichier, on_delete=models.CASCADE,null=True)
    history = HistoricalRecords()
    def __str__(self):
        return self.designation
    
    def save(self, *args, **kwargs):
        if self.qte_recue is None:
            self.qte_recue = self.qte
        super().save(*args, **kwargs)


class item(AutoReferenceGeneratorMixin):
    REFERENCE_PREFIX = 'ITEM-'
    REFERENCE_FIELD = 'reference_auto'
    """Concrete, trackable unit (asset) created from an `article` and located/assigned."""
    statut = [
        ('affecter', 'affecter'),
        ('non affecter', 'non affecter'), 
        
    ]
    reference_auto = models.CharField(max_length=255,blank=True,null=True)
    date_affectation = models.DateField(blank=True,null=True,auto_now_add=True)
    statut = models.CharField(choices=statut ,max_length = 250,default='non affecter')
    archive = models.BooleanField(default = False)
    date_archive = models.DateField(blank=True, null=True)
    affectation_personne=models.ForeignKey(Personne,on_delete=models.CASCADE,blank=True, null=True)
    numero_serie = models.CharField(max_length=250,blank=True,null=True,unique=False)
    emplacement = models.ForeignKey(emplacement, on_delete=models.CASCADE)
    departement = models.ForeignKey(departement, on_delete=models.CASCADE,unique=False,default=1)
    article = models.ForeignKey(article, on_delete=models.CASCADE)  
    tag = models.ForeignKey('masterdata.tag', on_delete=models.SET_NULL, blank=True, null=True, related_name='items')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()
    def __str__(self):
        return self.statut

    def calculate_residual_value(self, year=None):
        """Compute linear residual value of this item for a given year."""
        if not self.article:
            return None

        duree_amortissement = self.article.produit.duree_amourtissement
        prix_achat = self.article.prix_achat

        if duree_amortissement is None or prix_achat is None:
            return None

        taux_amortissement = (100 / duree_amortissement) / 100
        montant_annuel = taux_amortissement * prix_achat

        current_year = year if year is not None else datetime.now().year
        purchase_year = self.article.date_achat.year
        annee = current_year - purchase_year

        if annee > duree_amortissement:
            valeur_residuelle = prix_achat - (montant_annuel * duree_amortissement)
        else:
            valeur_residuelle = prix_achat - (montant_annuel * annee)

        return max(valeur_residuelle, 0)


class TransferHistorique(models.Model):
    """History of item transfers between locations, departments or people."""
    item_transfer = models.ForeignKey(item, on_delete=models.CASCADE)
    new_emplacement = models.ForeignKey(emplacement, on_delete=models.CASCADE, blank=True, null=True, related_name='new_emplacement_transfers')
    old_emplacement = models.ForeignKey(emplacement, on_delete=models.CASCADE, blank=True, null=True, related_name='old_emplacement_transfers')
    new_personne = models.ForeignKey(Personne, on_delete=models.CASCADE, blank=True, null=True, related_name='new_personne_transfers')
    old_personne = models.ForeignKey(Personne, on_delete=models.CASCADE, blank=True, null=True, related_name='old_personne_transfers')
    new_departement = models.ForeignKey(departement, on_delete=models.CASCADE, blank=True, null=True, related_name='new_departement_transfers')
    old_departement = models.ForeignKey(departement, on_delete=models.CASCADE, blank=True, null=True, related_name='old_departement_transfers')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()


class ArchiveItem(models.Model):
    """Archived items with comments explaining the reason/context."""

    MOTIF_CHOICES = [
        ('reforme', 'Réformé'),
        ('perdu', 'Perdu'),
        ('don', 'Don'),
        ('vendu', 'Vendu'),
        ('casse', 'Cassé'),
        ('vole', 'Volé'),
        ('retour_fournisseur', 'Retour fournisseur'),
        ('autre', 'Autre'),
    ]

    item_archive = models.ForeignKey(item, on_delete=models.CASCADE, related_name='archive_items')
    commentaire = models.CharField(max_length=250)
    motif = models.CharField(max_length=30, choices=MOTIF_CHOICES, default='autre')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()
