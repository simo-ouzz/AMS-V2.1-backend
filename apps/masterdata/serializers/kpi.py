from decimal import Decimal

from rest_framework import serializers

from masterdata.models import (
    categorie, type_tag, location, departement, Personne, item,
)


class CategorieItemCountSerializer(serializers.ModelSerializer):
    total_items = serializers.IntegerField(read_only=True)
    name = serializers.CharField(source='libelle', read_only=True)

    class Meta:
        model = categorie
        fields = ['name', 'total_items']


class TypeTagCountSerializer(serializers.ModelSerializer):
    total_items = serializers.IntegerField(read_only=True)
    name = serializers.CharField(source='nom', read_only=True)

    class Meta:
        model = type_tag
        fields = ['name', 'total_items']
        
class ArticleCountSerializer(serializers.Serializer):
    count = serializers.IntegerField()

class tagsCountSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    
class ArchivedItemsCountSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    
class AmortizationCountSerializer(serializers.Serializer):
    total_amortized = serializers.IntegerField()
    total_non_amortized = serializers.IntegerField()
    

class FinancialValueSerializer(serializers.Serializer):
    name = serializers.CharField()
    value = serializers.DecimalField(max_digits=10, decimal_places=2)

    def validate_value(self, value):
        if value is None or not isinstance(value, (int, float, Decimal)):
            raise serializers.ValidationError("Total residual value must be a valid number.")
        return value

class LocationWithEmplacementCountSerializer(serializers.ModelSerializer):
    value = serializers.IntegerField(read_only=True)

    class Meta:
        model = location
        fields = ['nom', 'value']
        
class DepartementCountSerializer(serializers.ModelSerializer):
    value = serializers.SerializerMethodField()

    class Meta:
        model = departement
        fields = ['nom', 'value']

    def get_value(self, obj):
        return obj.item_set.count()
    
class PersonneItemSummarySerializer(serializers.ModelSerializer):
    nom_complet = serializers.SerializerMethodField()
    valeur_residuelle_totale = serializers.SerializerMethodField()
    quantite_items = serializers.IntegerField(source='item_set.count', read_only=True)

    class Meta:
        model = Personne
        fields = ['nom_complet', 'quantite_items', 'valeur_residuelle_totale']

    def get_nom_complet(self, personne):
        return f"{personne.nom} {personne.prenom}"

    def get_valeur_residuelle_totale(self, personne):
        items = item.objects.filter(affectation_personne=personne)
        return sum(i.calculate_residual_value() for i in items)
