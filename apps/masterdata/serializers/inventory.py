from rest_framework import serializers

from core.mixins.serializer_mixins import UserFullNameMixin
from masterdata.models import (
    inventaire, inventaire_emplacement, detail_inventaire, item,
)


class InventaireEmplacementSerializer(serializers.ModelSerializer):
    class Meta:
        model = inventaire_emplacement
        fields = '__all__'

class InventairesEmplacementSerializer(serializers.ModelSerializer):
    emplacement_nom = serializers.CharField(source='emplacement.nom')
    inventaire_nom = serializers.CharField(source='inventaire.nom')
    inventaire_id = serializers.CharField(source='inventaire.id')
    date_creation = serializers.CharField(source='inventaire.date_creation')
    emplacement_id = serializers.CharField(source='emplacement.id')

    class Meta:
        model = inventaire_emplacement
        fields = ('id','statut','emplacement_id',"inventaire_id" ,'date_creation', 'emplacement_nom', 'inventaire_nom')


class InventaireSerializer(UserFullNameMixin, serializers.ModelSerializer):
    user = serializers.SerializerMethodField()
    emplacement = serializers.SerializerMethodField()
    
    class Meta:
        model = inventaire
        fields = ('id', 'reference', 'nom', 'statut','emplacement', 'user', 'created_at')

    def get_emplacement(self, obj):
        try:
            rel_qs = getattr(obj, 'inventaire_emplacement_set', None)
            if rel_qs is not None:
                first_link = rel_qs.all().select_related('emplacement').order_by('id').first()
                if first_link and getattr(first_link, 'emplacement', None):
                    return first_link.emplacement.nom
        except Exception:
            pass

        try:
            first_link = (
                inventaire_emplacement.objects
                .filter(inventaire_id=obj.id)
                .select_related('emplacement')
                .order_by('id')
                .values_list('emplacement__nom', flat=True)
                .first()
            )
            if first_link:
                return first_link
        except Exception:
            pass

        return None


class InventaireLocationSerializer(UserFullNameMixin, serializers.ModelSerializer):
    user = serializers.SerializerMethodField()
    libelle = serializers.CharField(source='nom', read_only=True)
    location = serializers.SerializerMethodField()
    
    class Meta:
        model = inventaire
        fields = ('id', 'reference', 'libelle', 'statut', 'location', 'user', 'date_creation', 'created_at')

    def get_location(self, obj):
        try:
            inv_emp_qs = getattr(obj, 'inventaire_emplacement_set', None)
            if inv_emp_qs is not None:
                first_link = inv_emp_qs.all().order_by('id').first()
                if first_link and hasattr(first_link, 'emplacement'):
                    if hasattr(first_link.emplacement, 'zone') and first_link.emplacement.zone:
                        if hasattr(first_link.emplacement.zone, 'location') and first_link.emplacement.zone.location:
                            return first_link.emplacement.zone.location.nom
            
            location_nom = (
                inventaire_emplacement.objects
                .filter(inventaire_id=obj.id)
                .select_related('emplacement__zone__location')
                .order_by('id')
                .values_list('emplacement__zone__location__nom', flat=True)
                .first()
            )
            return location_nom if location_nom else None
        except Exception:
            return None


class InventaireZoneSerializer(UserFullNameMixin, serializers.ModelSerializer):
    user = serializers.SerializerMethodField()
    libelle = serializers.CharField(source='nom', read_only=True)
    zone = serializers.SerializerMethodField()
    
    class Meta:
        model = inventaire
        fields = ('id', 'reference', 'libelle', 'statut', 'zone', 'user', 'date_creation', 'created_at')

    def get_zone(self, obj):
        try:
            inv_emp_qs = getattr(obj, 'inventaire_emplacement_set', None)
            if inv_emp_qs is not None:
                first_link = inv_emp_qs.all().order_by('id').first()
                if first_link and hasattr(first_link, 'emplacement'):
                    if hasattr(first_link.emplacement, 'zone') and first_link.emplacement.zone:
                        return first_link.emplacement.zone.nom
            
            zone_nom = (
                inventaire_emplacement.objects
                .filter(inventaire_id=obj.id)
                .select_related('emplacement__zone')
                .order_by('id')
                .values_list('emplacement__zone__nom', flat=True)
                .first()
            )
            return zone_nom if zone_nom else None
        except Exception:
            return None


class InventaireDepartementSerializer(UserFullNameMixin, serializers.ModelSerializer):
    user = serializers.SerializerMethodField()
    libelle = serializers.CharField(source='nom', read_only=True)
    departement = serializers.CharField(source='departement.nom', read_only=True)
    
    class Meta:
        model = inventaire
        fields = ('id', 'reference', 'libelle', 'statut', 'departement', 'user', 'date_creation', 'created_at')


class InventaireEmplacementDetailSerializer(serializers.ModelSerializer):
    emplacement = serializers.CharField(source='emplacement.nom', read_only=True)
    operateur = serializers.SerializerMethodField()
    etat = serializers.BooleanField(source='start_at', read_only=True)
    expected_items = serializers.SerializerMethodField()
    
    class Meta:
        model = inventaire_emplacement
        fields = ('id', 'emplacement', 'operateur', 'statut', 'etat', 'expected_items', 'created_at')
    
    def get_expected_items(self, obj):
        try:
            return item.objects.filter(emplacement_id=obj.emplacement_id).count()
        except Exception:
            return 0

    def get_operateur(self, obj):
        try:
            if obj.affceted_at:
                nom = obj.affceted_at.nom or ''
                prenom = obj.affceted_at.prenom or ''
                return f"{nom} {prenom}".strip()
            return ""
        except Exception:
            return ""


class InventaireEmplacementSimpleSerializer(serializers.ModelSerializer):
    emplacement_id = serializers.IntegerField(source='emplacement.id', read_only=True)
    emplacement_nom = serializers.CharField(source='emplacement.nom', read_only=True)
    
    class Meta:
        model = inventaire_emplacement
        fields = ('id', 'emplacement_id', 'emplacement_nom', 'statut', 'created_at')


class DetailInventaireSerializer(serializers.ModelSerializer):
    inventaire = serializers.PrimaryKeyRelatedField(queryset=inventaire.objects.all())
    item = serializers.PrimaryKeyRelatedField(queryset=item.objects.all())
    
    class Meta:
        model = detail_inventaire
        fields = ['inventaire', 'item', 'etat']

    def create(self, validated_data):
        return detail_inventaire.objects.create(**validated_data)
    
class CreatDetailInventaireSerializer(serializers.ModelSerializer):
    class Meta:
        model = detail_inventaire
        fields = ['inventaire_emplacement', 'item', 'etat']


class DetailInventairesSerializer(serializers.ModelSerializer):
    """Serializer for inventory lines enriched with item/emplacement labels."""
    item = serializers.SerializerMethodField()
    emplacement = serializers.SerializerMethodField()
    item_id = serializers.SerializerMethodField()
    reference = serializers.SerializerMethodField()
    emplacement_origine = serializers.SerializerMethodField()
    created_at = serializers.SerializerMethodField()
    start_at = serializers.SerializerMethodField()

    class Meta:
        model = detail_inventaire
        fields = ['item_id', 'reference', 'emplacement_origine', 'item', 'emplacement', 'etat', 'start_at', 'created_at']

    def get_emplacement_origine(self,obj):
        return obj.item.emplacement.nom
    def get_item(self, obj):
        return  obj.item.article.designation
    def get_item_id(self,obj):
        return obj.item.id
    def get_reference(self,obj):
        return obj.item.article.code_article

    def get_emplacement(self, obj):
        return obj.inventaire_emplacement.emplacement.nom

    def get_start_at(self, obj):
        if obj.inventaire_emplacement:
            return obj.inventaire_emplacement.start_at
        return False

    def get_created_at(self, obj):
        return obj.created_at.strftime('%d/%m/%Y-%H:%M:%S')
