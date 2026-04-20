from rest_framework import serializers
from masterdata.models import (
    produit, marque, departement, type_tag, fournisseur,
    nature, categorie, Personne, location, zone, emplacement, operation, tag,
    tagEmplacement,
)


class ProduitSerializer(serializers.ModelSerializer):
    """Read-only serializer exposing core product family fields."""
    categorie = serializers.StringRelatedField(source='categorie.libelle')

    class Meta:
        model = produit
        fields = ['id','libelle', 'code_produit', 'categorie', 'duree_amourtissement', 'statut', 'created_at', 'updated_at']

class MarqueSerializer(serializers.ModelSerializer):
    class Meta:
        model = marque
        fields = '__all__'

class DepartementSerializer(serializers.ModelSerializer):
    class Meta:
        model = departement
        fields = '__all__'

class TypeTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = type_tag
        fields = '__all__'

class FournisseurSerializer(serializers.ModelSerializer):
    class Meta:
        model = fournisseur
        fields = '__all__'

class NatureSerializer(serializers.ModelSerializer):
    class Meta:
        model = nature
        fields = '__all__'

class CategorieSerializer(serializers.ModelSerializer):
    class Meta:
        model = categorie
        fields = '__all__'

class PersonneSerializer(serializers.ModelSerializer):
    class Meta:
        model = Personne
        fields = '__all__'

class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = location
        fields = '__all__'

class ZoneSerializer(serializers.ModelSerializer):
    class Meta:
        model = zone
        fields = '__all__'

class EmplacementSerializer(serializers.ModelSerializer):
    location = serializers.SerializerMethodField()
    tag = serializers.SerializerMethodField()
    tag_type = serializers.SerializerMethodField()
    class Meta:
        model = emplacement
        fields = '__all__'
    def get_location(self, obj):
        return obj.zone.location.nom if obj.zone.location.nom else None
    
    def get_tag(self, obj):
        return obj.tag.reference if obj.tag else None

    def get_tag_type(self, obj):
        return obj.tag.type.nom if obj.tag and obj.tag.type else None

class OperationSerializer(serializers.ModelSerializer):
    class Meta:
        model = operation
        fields = '__all__'

class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = tag
        fields = '__all__'


# ---------------------------------------------------------------------------
# Write serializers for CRUD operations
# ---------------------------------------------------------------------------

class PersonneWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Personne
        fields = ['prenom', 'nom', 'gender']


class CategorieWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = categorie
        fields = ['libelle']


class ProduitWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = produit
        fields = ['libelle', 'categorie', 'duree_amourtissement', 'statut']


class NatureWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = nature
        fields = ['libelle']


class FournisseurWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = fournisseur
        fields = ['nom', 'ice', 'tel', 'adresse']


class DepartementWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = departement
        fields = ['nom']


class MarqueWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = marque
        fields = ['nom']


class TypeTagWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = type_tag
        fields = ['nom']


class OperationWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = operation
        fields = ['reference']


class LocationWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = location
        fields = ['nom']


class ZoneWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = zone
        fields = ['nom', 'location']


class EmplacementWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = emplacement
        fields = ['nom', 'zone']


class TagEmplacementSerializer(serializers.ModelSerializer):
    class Meta:
        model = tagEmplacement
        fields = '__all__'


class TagWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = tag
        fields = ['reference', 'statut', 'type', 'affecter']


class TagEmplacementWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = tagEmplacement
        fields = ['reference', 'statut', 'type', 'affecter']
