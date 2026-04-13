from rest_framework import serializers

from masterdata.models import TagHistory, tagEmplacement, emplacement


class TagHistorySerializer(serializers.ModelSerializer):
    old_tag_reference = serializers.CharField(source='old_tag.reference', read_only=True)
    new_tag_reference = serializers.CharField(source='new_tag.reference', read_only=True)
    item_designation = serializers.CharField(source='item.article.designation', read_only=True)
    user_full_name = serializers.SerializerMethodField()

    class Meta:
        model = TagHistory
        fields = ['id', 'item_designation', 'old_tag_reference', 'new_tag_reference', 'user_full_name']

    def get_user_full_name(self, obj):
        if obj.changed_by:
            return f"{obj.changed_by.nom} {obj.changed_by.prenom}"
        return "Unknown User"


class TagAffectationSerializer(serializers.Serializer):
    emplacementId = serializers.IntegerField()
    tag_reference = serializers.CharField(max_length=250)

    def validate(self, data):
        try:
            emplacement_instance = emplacement.objects.get(id=data['emplacementId'])
        except emplacement.DoesNotExist:
            raise serializers.ValidationError("L'emplacement avec cet ID n'existe pas.")
        
        try:
            tag_instance = tagEmplacement.objects.get(reference=data['tag_reference'])
        except tagEmplacement.DoesNotExist:
            raise serializers.ValidationError("Le tag avec cette référence n'existe pas.")
        
        if tag_instance.affecter:
            raise serializers.ValidationError("Ce tag est déjà affecté à un autre emplacement.")
        
        data['emplacement_instance'] = emplacement_instance
        data['tag_instance'] = tag_instance
        return data
