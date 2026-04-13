import os

from django.conf import settings
from django.core.exceptions import ValidationError
from urllib.parse import urljoin
from rest_framework import serializers

from masterdata.models import operation_article


class OperationItemsSerializer(serializers.ModelSerializer):
    """Lightweight view of item operation attachments and references."""
    item_designation = serializers.SerializerMethodField()
    operation_reference = serializers.SerializerMethodField()
    tag = serializers.SerializerMethodField()

    class Meta:
        model = operation_article
        fields = ['id', 'operation_reference', 'item_designation', 'prix', 'date_operation', 'commentaire', 'attachement', 'tag', 'created_at', 'updated_at']

    def get_item_designation(self, obj):
        if obj.item and obj.item.article:
            return obj.item.article.designation
        return None

    def get_tag(self, obj):
        if obj.item and obj.item.tag.reference:
            return obj.item.tag.reference
        return None
    
    def get_operation_reference(self, obj):
        if obj.operation:
            return obj.operation.reference
        return None

    def to_representation(self, instance):
        representation = super().to_representation(instance)

        if instance.attachement:
            file_url = urljoin(settings.SITE_URL, instance.attachement.url)
            representation['attachement_url'] = file_url
            representation['attachement_file'] = file_url
        else:
            representation['attachement_url'] = 'auccun fichier'
            representation['attachement_file'] = 'auccun fichier'

        return representation


class OperationItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = operation_article
        fields = ['item', 'operation', 'prix', 'date_operation', 'attachement', 'commentaire']

    def validate_attachement(self, value):
        if value:
            allowed_extensions = ['jpg', 'jpeg', 'png', 'gif', 'pdf', 'doc', 'docx']
            ext = os.path.splitext(value.name)[1][1:].lower()

            if ext not in allowed_extensions:
                raise ValidationError(f'Unsupported file extension. Allowed extensions are: {", ".join(allowed_extensions)}')
        
        return value
