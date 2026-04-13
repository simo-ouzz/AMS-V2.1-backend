from datetime import datetime
from urllib.parse import urljoin

from django.conf import settings
from rest_framework import serializers

from masterdata.models import article, produit, marque, fournisseur, nature


class ArticleSerializer(serializers.ModelSerializer):
    """Detailed article representation with computed image URL and category name."""
    image_url = serializers.SerializerMethodField()  
    date_reception = serializers.SerializerMethodField()
    categorie = serializers.CharField(source='produit.categorie.libelle', read_only=True)
    fournisseur = serializers.CharField(source='fournisseur.nom', read_only=True)
    class Meta:
        model = article
        fields = '__all__'
    def get_date_reception(self, obj):
        if isinstance(obj.date_reception, datetime):
            return obj.date_reception.date()
        return obj.date_reception 
    def get_image_url(self, obj):
        if obj.image:  
            return obj.image.url  
        return None  
        
class EditArticleSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = article
        fields = '__all__'

    def get_image_url(self, obj):
        request = self.context.get('request')
        if obj.image:
            return request.build_absolute_uri(obj.image.url)
        return None

class ArticleSerializeres(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()
    produit = serializers.CharField(source='produit.libelle', read_only=True)
    statut = serializers.SerializerMethodField()
    fournisseur = serializers.CharField(source='fournisseur.nom', read_only=True)
    nature = serializers.CharField(source='nature.libelle', read_only=True)
    marque = serializers.CharField(source='marque.nom', read_only=True)
    categorie = serializers.CharField(source='produit.categorie.libelle', read_only=True)

    class Meta:
        model = article
        fields = [
            'id', 'produit', 'nature', 'statut', 'fournisseur', 'image_url', 'categorie',
            'code_article', 'designation', 'date_achat', 'numero_comptable',
            'couleur', 'poids', 'volume', 'langueur', 'hauteur', 'largeur',
            'date_expiration', 'date_peremption', 'date_reception',
            'prix_achat', 'attachement1', 'attachement2', 'marque', 
            'N_facture', 'attachement3', 'qte_recue', 'qte', 'created_at', 'updated_at'
        ]

    def get_statut(self, obj):
        return obj.produit.statut

    def get_image_url(self, obj):
        if obj.image:
            return urljoin(settings.SITE_URL, obj.image.url)  
        return None

    def get_fournisseur(self, obj):
        return obj.fournisseur.nom

class EditItemArticleSerializer(serializers.ModelSerializer):
    categorie = serializers.SerializerMethodField()

    class Meta:
        model = article
        fields = [
            'produit', 'nature', 'fournisseur',  'categorie', 'marque','N_facture'
        ]
    def get_categorie(self, obj):
        if obj.produit and obj.produit.categorie:
            return obj.produit.categorie.id
        return None


class CreateOneArticleSerializer(serializers.ModelSerializer):
    class Meta:
        model = article
        fields = [
            'id', 'produit', 'nature', 'fournisseur', 'image',
             'designation', 'date_achat', 'numero_comptable',
            'couleur', 'poids', 'volume', 'langueur', 'hauteur', 'largeur',
            'date_expiration', 'date_peremption', 'date_reception',
            'prix_achat', 'attachement1', 'attachement2', 'marque',
            'N_facture', 'attachement3', 'qte',
        ]
    extra_kwargs = {'user': {'read_only': True}}

    def create(self, validated_data):
        if 'qte' not in validated_data or validated_data['qte'] is None:
            validated_data['qte'] = 1
        return super().create(validated_data)

       
class CreateArticleSerializer(serializers.ModelSerializer):
    class Meta:
        model = article
        fields = [
            'id', 'produit', 'nature', 'fournisseur', 'image',
            'code_article', 'designation', 'date_achat', 'numero_comptable',
            'couleur', 'poids', 'volume', 'langueur', 'hauteur', 'largeur',
            'date_expiration', 'date_peremption', 'date_reception',
            'prix_achat', 'attachement1', 'attachement2', 'marque', 
            'N_facture', 'attachement3', 'qte',
        ]

    error_messages = {
        'produit': {
            'blank': 'Le champ produit ne peut pas être vide.',
            'required': 'Veuillez spécifier un produit.',
        },
        'qte': {
            'blank': 'Le champ quantité ne peut pas être vide.',
            'invalid': 'La quantité doit être un nombre valide.',
        },
        'N_facture': {
            'blank': 'Le champ numéro de facture ne peut pas être vide.',
        },
        'code_article': {
            'blank': 'Le champ code article ne peut pas être vide.',
        },
        'designation': {
            'blank': 'Le champ désignation ne peut pas être vide.',
        },
        'date_expiration': {
            'invalid': 'Le format de la date d\'expiration est incorrect. Veuillez utiliser le format YYYY-MM-DD.',
        },
    }

    def validate(self, attrs):
        attrs['produit'] = self.validate_relation(attrs.get('produit'), produit, 'libelle', "produit")
        attrs['marque'] = self.validate_relation(attrs.get('marque'), marque, 'nom', "marque")
        attrs['fournisseur'] = self.validate_relation(attrs.get('fournisseur'), fournisseur, 'nom', "fournisseur")
        attrs['nature'] = self.validate_relation(attrs.get('nature'), nature, 'libelle', "nature")

        for date_field in ['date_peremption', 'date_expiration', 'date_reception', 'date_achat']:
            if date_field in attrs:
                attrs[date_field] = self.validate_date(attrs[date_field], date_field)

        return attrs

    def validate_relation(self, value, model, field_name, field_label):
        if value:
            try:
                return model.objects.get(**{field_name: value})
            except model.DoesNotExist:
                raise serializers.ValidationError({field_label: f"{field_label.capitalize()} '{value}' non trouvé."})
        return value

    def validate_date(self, date_value, field_label):
        if isinstance(date_value, str):
            try:
                return datetime.strptime(date_value, '%Y-%m-%d').date()
            except ValueError:
                raise serializers.ValidationError({field_label: f"Date invalide pour '{date_value}'."})
        return date_value

    def create(self, validated_data):
        return article.objects.create(**validated_data)    


class UpdateItemArticleSerializer(serializers.ModelSerializer):
    produit = serializers.IntegerField(write_only=True, required=False)
    nature = serializers.IntegerField(write_only=True, required=False, allow_null=True)  
    fournisseur = serializers.IntegerField(write_only=True, required=False)
    marque = serializers.IntegerField(write_only=True, required=False, allow_null=True)  
    categorie = serializers.IntegerField(write_only=True, required=False)  
    N_facture = serializers.CharField(required=False)

    class Meta:
        model = article
        fields = ['produit', 'nature', 'fournisseur', 'categorie', 'marque', 'N_facture']

    def update(self, instance, validated_data):
        instance.produit_id = validated_data.get('produit', instance.produit_id)
        instance.nature_id = validated_data.get('nature', instance.nature_id)  
        instance.fournisseur_id = validated_data.get('fournisseur', instance.fournisseur_id)
        instance.marque_id = validated_data.get('marque', instance.marque_id)

        if 'N_facture' in validated_data:
            instance.N_facture = validated_data['N_facture']

        instance.save()
        instance.refresh_from_db()
        return instance
