from rest_framework import serializers

from masterdata.models import TransferHistorique


class TransferHistoriqueSimpleSerializer(serializers.ModelSerializer):
    """Simple serializer for transfer history (IDs only)."""
    class Meta:
        model = TransferHistorique
        fields = '__all__'


class TransferHistoriqueSerializer(serializers.ModelSerializer):
    """Detailed serializer for transfer history with readable names."""
    item_reference = serializers.CharField(source='item_transfer.reference_auto', read_only=True)
    item_designation = serializers.CharField(source='item_transfer.article.designation', read_only=True)

    old_emplacement_nom = serializers.CharField(source='old_emplacement.nom', read_only=True)
    new_emplacement_nom = serializers.CharField(source='new_emplacement.nom', read_only=True)

    old_departement_nom = serializers.CharField(source='old_departement.nom', read_only=True)
    new_departement_nom = serializers.CharField(source='new_departement.nom', read_only=True)

    old_personne_nom = serializers.SerializerMethodField()
    new_personne_nom = serializers.SerializerMethodField()

    class Meta:
        model = TransferHistorique
        fields = [
            'id',
            'created_at',
            'updated_at',
            'item_reference',
            'item_designation',
            'old_emplacement_nom',
            'new_emplacement_nom',
            'old_departement_nom',
            'new_departement_nom',
            'old_personne_nom',
            'new_personne_nom'
        ]

    def get_old_personne_nom(self, obj):
        if obj.old_personne:
            return f"{obj.old_personne.nom} {obj.old_personne.prenom}"
        return None

    def get_new_personne_nom(self, obj):
        if obj.new_personne:
            return f"{obj.new_personne.nom} {obj.new_personne.prenom}"
        return None
