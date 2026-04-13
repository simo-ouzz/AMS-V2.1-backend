from rest_framework import serializers

from masterdata.models import item, ArchiveItem
from .article import ArticleSerializeres, EditItemArticleSerializer, ArticleSerializer
from .master import EmplacementSerializer, DepartementSerializer, PersonneSerializer


class EditItemSerializer(serializers.ModelSerializer):
    article = EditItemArticleSerializer()
    
    class Meta:
        model = item
        fields = ['article']

    def get_produit_categorie(self, obj):
        if obj.article and obj.article.produit:
            return obj.article.produit.categorie.libelle
        return None
    

class ItemsSerializer(serializers.ModelSerializer):
    """Aggregate representation of an `item` including nested article and context fields."""
    emplacement = serializers.StringRelatedField(source='emplacement.nom', read_only=True)
    zone = serializers.StringRelatedField(source='emplacement.zone.nom', read_only=True)
    departement = serializers.StringRelatedField(source='departement.nom', read_only=True)
    affectation_personne_full_name = serializers.SerializerMethodField()
    article = ArticleSerializeres()
    tag = serializers.StringRelatedField(source='tag.reference', read_only=True)
    tag_type = serializers.StringRelatedField(source='tag.type.nom', read_only=True)
    valeur_residuelle = serializers.SerializerMethodField()
    produit_categorie = serializers.SerializerMethodField()
    commentaire = serializers.SerializerMethodField()
    motif = serializers.SerializerMethodField()
    fournisseur = serializers.StringRelatedField(source='article.fournisseur.nom', read_only=True)

    class Meta:
        model = item
        fields = [
            'id',
            'date_affectation',
            'emplacement',
            'zone',
            'departement',
            'article',
            'valeur_residuelle',
            'tag',
            'tag_type',
            'affectation_personne_full_name',
            'numero_serie',
            'fournisseur',
            'archive',
            'created_at',
            'updated_at',
            'statut',
            'produit_categorie',  
            'commentaire',
            'motif',
        ]

    def get_affectation_personne_full_name(self, obj):
        return f"{obj.affectation_personne.nom} {obj.affectation_personne.prenom}" if obj.affectation_personne else None

    def get_produit_categorie(self, obj):
        if obj.article and obj.article.produit:
            return obj.article.produit.categorie.libelle
        return None
    
    def get_zone(self,obj):
        return obj.emplacement.zone

    def get_valeur_residuelle(self, obj):
        return obj.calculate_residual_value()

    def get_commentaire(self, obj):
        last_archive_item = obj.archive_items.last()
        return last_archive_item.commentaire if last_archive_item else None

    def get_motif(self, obj):
        last_archive_item = obj.archive_items.last()
        return last_archive_item.motif if last_archive_item else None


class ItemNewSerializer(serializers.ModelSerializer):
    article = ArticleSerializer(read_only=True)
    emplacement = EmplacementSerializer(read_only=True)
    departement = DepartementSerializer(read_only=True)
    affectation_personne = PersonneSerializer(read_only=True)

    class Meta:
        model = item
        fields = ['reference_auto', 'statut', 'archive', 'numero_serie', 'date_affectation',
                  'date_archive', 'emplacement', 'departement', 'affectation_personne',
                  'article', 'created_at', 'updated_at']


class ArchiveItemSerializer(serializers.ModelSerializer):
    """Serializer for archived item representation."""
    item_id = serializers.IntegerField(source="item_archive.id", read_only=True)
    item_reference = serializers.CharField(
        source="item_archive.reference_auto", read_only=True
    )
    item_designation = serializers.CharField(
        source="item_archive.article.designation", read_only=True
    )
    item_numero_serie = serializers.CharField(
        source="item_archive.numero_serie", read_only=True
    )

    class Meta:
        model = ArchiveItem
        fields = [
            "id",
            "item_id",
            "item_reference",
            "item_designation",
            "item_numero_serie",
            "commentaire",
            "motif",
            "created_at",
            "updated_at",
        ]


class ArchiveItemExcelImportSerializer(serializers.Serializer):
    """Input serializer for Excel import of item archives."""
    file = serializers.FileField()
    skip_errors = serializers.BooleanField(default=True)


class ArchiveItemBatchSerializer(serializers.Serializer):
    """Input serializer for batch archiving."""
    items_id = serializers.ListField(
        child=serializers.IntegerField(min_value=1), allow_empty=False
    )
    motif = serializers.CharField(required=False, default='autre')


class ItemCountSerializer(serializers.Serializer):
    count = serializers.IntegerField()
