from django_filters import rest_framework as django_filters
from django.views import View
from masterdata.config.CustomPageNumberPagination import CustomPageNumberPagination
from masterdata.config.ArticleFiltrage import ArticleFilter
from masterdata.config.InventaireFilterage import InventaireFilter
from masterdata.config.ItemFilterage import ItemFilter
from masterdata.serializers import *
from masterdata.models import *
from masterdata.services.items import (
    ArchiveItemsImportError,
    archive_or_unarchive_item_service,
    archive_items_batch_service,
    import_archive_items_from_excel_service,
    list_archive_items_for_user,
)
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import pandas as pd
from rest_framework.pagination import PageNumberPagination
from django.db.models import Q
from django.http import HttpResponse
from rest_framework import generics
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from datatables import ServerSideDataTableView
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth.models import Permission
from django.shortcuts import render, redirect
from django.contrib import messages


class TagCreateView(APIView):
    def post(self, request):
        user = request.user

        # S'assurer que l'utilisateur est authentifié
        if not user.is_authenticated:
            return Response(
                {"error": "Utilisateur non authentifié."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        references = request.data.get(
            "reference", []
        )  # Obtenir la liste des références depuis les données de la requête
        type_tag = request.data.get("type_tag", None)

        if type_tag is None:
            return Response(
                {"error": "Merci de sélectionner un type."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Vérifier si 'references' est bien une liste
        if not isinstance(references, list):
            return Response(
                {"error": "'reference' doit être une liste."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Récupérer toutes les références existantes pour l'utilisateur
        existing_tags = tag.objects.filter(compte=user.compte.id, type=type_tag)
        existing_references = existing_tags.values_list("reference", flat=True)

        # Vérifier si des références fournies existent déjà
        duplicates = [ref for ref in references if ref in existing_references]
        if duplicates:
            return Response(
                {
                    "error": f"Les tags avec les références suivantes existent déjà : {', '.join(duplicates)}."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        created_tags = []

        try:
            with transaction.atomic():  # Utiliser une transaction pour garantir l'intégrité des données
                for reference in references:
                    # Créer un serializer pour chaque référence
                    serializer = TagSerializer(
                        data={
                            "reference": reference,
                            "compte": user.compte.id,
                            "type": type_tag,
                        }
                    )
                    serializer.is_valid(raise_exception=True)
                    serializer.save()  # Enregistrer l'objet tag
                    created_tags.append(serializer.data)

            return Response(
                {"message": "Tags créés avec succès.", "tags": created_tags},
                status=status.HTTP_201_CREATED,
            )

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


from django.db.models import ObjectDoesNotExist
from django.core.exceptions import ObjectDoesNotExist
from masterdata.models import tag, item, emplacement, inventaire
from rest_framework.response import Response
from rest_framework import status


class UpdateTagAPIView(APIView):
    def post(self, request, *args, **kwargs):

        old_tag_id = request.data.get("old_tag_id")
        new_tag_id = request.data.get("new_tag_id")
        user_id = request.user.id
        try:
            old_tag = tag.objects.filter(reference=old_tag_id).first()
        except tag.DoesNotExist:
            return Response(
                {"error": "tag l’ancien non trouvé."}, status=status.HTTP_404_NOT_FOUND
            )
        try:
            new_tag = tag.objects.filter(reference=new_tag_id).first()
        except tag.DoesNotExist:
            return Response(
                {"error": "nouveau tag non trouvé."}, status=status.HTTP_404_NOT_FOUND
            )

        # Récupérer l'utilisateur qui effectue l'action
        user_instance = get_object_or_404(UserWeb, id=user_id)
        # Récupérer l'item associé à l'ancien tag
        try:
            item_instance = item.objects.get(tag=old_tag)
        except item.DoesNotExist:
            return Response(
                {"error": "Item associé à l’ancien tag non trouvé."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Créer une entrée dans TagHistory en passant les instances des objets
        old_tag.affecter = False
        old_tag.statut = "off"
        old_tag.save()
        TagHistory.objects.create(
            item=item_instance,
            old_tag=old_tag,  # Passer l'instance du tag
            new_tag=new_tag,  # Passer l'instance du tag
            changed_by=user_instance,  # Passer l'instance de l'utilisateur
        )

        # Mettre à jour le tag de l'item
        item_instance.tag = new_tag  # Assigner l'instance du tag
        item_instance.save()

        return Response(
            {"message": "Tag mis à jour avec succès."}, status=status.HTTP_200_OK
        )


class TagHistoryListAPIView(ServerSideDataTableView):
    """
    Vue pour lister l'historique des changements de tags d'un item avec support DataTable
    
    Fonctionnalités automatiques :
    - Pagination côté serveur
    - Recherche globale et par colonnes
    - Tri multi-colonnes
    - Filtres avancés
    - Export Excel/CSV
    """
    model = TagHistory
    serializer_class = TagHistorySerializer
    permission_classes = [IsAuthenticated]
    
    # Configuration de l'export
    export_filename = 'tag_history'
    
    # Configuration DataTable
    search_fields = [
        'old_tag__reference',
        'new_tag__reference',
        'item__article__designation',
        'item__reference_auto',
        'changed_by__nom',
        'changed_by__prenom'
    ]
    
    # Mapping des colonnes frontend -> backend
    column_field_mapping = {
        'id': 'id',
        'old_tag': 'old_tag__reference',
        'new_tag': 'new_tag__reference',
        'item_designation': 'item__article__designation',
        'item_reference': 'item__reference_auto',
        'changed_by': 'changed_by__nom',
        'created_at': 'created_at'
    }

    # Configuration de pagination
    default_page_size = 10
    max_page_size = 100

    def get_queryset(self):
        """Queryset de base - historique d'un item spécifique"""
        item_id = self.kwargs.get('item_id')
        
        if not item_id:
            return TagHistory.objects.none()
            
        return TagHistory.objects.filter(
            item__id=item_id
        ).select_related(
            'item',
            'item__article',
            'old_tag',
            'new_tag',
            'changed_by'
        ).order_by('-created_at')
    
    def get(self, request, item_id, *args, **kwargs):
        """Override pour passer item_id au queryset"""
        self.kwargs['item_id'] = item_id
        return super().get(request, *args, **kwargs)


class AffecterTagEmplacementView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = TagAffectationSerializer(data=request.data)
        if serializer.is_valid():
            emplacement_instance = serializer.validated_data["emplacement_instance"]
            tag_instance = serializer.validated_data["tag_instance"]

            # Affecter le tag à l'emplacement
            emplacement_instance.tag = tag_instance
            emplacement_instance.save()
            # Marquer le tag comme affecté
            tag_instance.affecter = True
            tag_instance.save()

            return Response(
                {"message": "Tag affecté à l'emplacement avec succès."},
                status=status.HTTP_200_OK,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AssignTagToEmplacementAPIView(APIView):
    def post(self, request):
        # Récupérer les données du corps de la requête
        emplacement_id = request.data.get("emplacement_id")
        tag_reference = request.data.get("tag_reference")

        # Vérifier que les données requises sont présentes
        if not emplacement_id:
            return Response(
                {"error": "Emplacement ID not provided"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not tag_reference:
            return Response(
                {"error": "Tag reference not provided"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            # Récupérer l'emplacement
            emplacement_instance = emplacement.objects.get(pk=emplacement_id)
        except emplacement.DoesNotExist:
            return Response(
                {"error": "Emplacement not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            # Récupérer le tag
            tag_instance = tagEmplacement.objects.get(reference=tag_reference)
        except tagEmplacement.DoesNotExist:
            return Response(
                {"error": "Tag not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Vérifier si l'emplacement a déjà un tag
        if emplacement_instance.tag:
            return Response(
                {"error": "This emplacement already has a tag assigned"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Assigner le tag à l'emplacement
        emplacement_instance.tag = tag_instance
        emplacement_instance.save()

        return Response(
            {"message": "Tag successfully assigned to emplacement"},
            status=status.HTTP_200_OK,
        )


# ── Tag Delete ─────────────────────────────────────────────────────────────

class TagDeleteAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        compte = request.user.compte
        if not compte:
            return Response(
                {"error": "No associated account found"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            obj = tag.objects.get(pk=pk, compte=compte)
        except tag.DoesNotExist:
            return Response({"error": "Tag not found"}, status=status.HTTP_404_NOT_FOUND)
        if obj.affecter:
            return Response(
                {"error": "Cannot delete a tag that is currently assigned"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class TagEmplacementDeleteAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        compte = request.user.compte
        if not compte:
            return Response(
                {"error": "No associated account found"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            obj = tagEmplacement.objects.get(pk=pk, compte=compte)
        except tagEmplacement.DoesNotExist:
            return Response({"error": "Tag emplacement not found"}, status=status.HTTP_404_NOT_FOUND)
        if obj.affecter:
            return Response(
                {"error": "Cannot delete a tag that is currently assigned"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

