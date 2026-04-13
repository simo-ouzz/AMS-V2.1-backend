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


class UpdateArticleEmplacement(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request):
        try:

            user = request.user
            tag_references = request.data.get("tag_reference", [])
            emplacement_id = request.data.get("emplacement_id", None)
            departement_id = request.data.get("departement_id", None)
            personne_id = request.data.get("personne_id", None)
            if not isinstance(tag_references, list):
                return Response(
                    "Les références de tag doivent être fournies sous forme de liste.",
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Rechercher les tags en fonction des références
            tags_objs = tag.objects.filter(
                reference__in=tag_references, compte=user.compte
            )

            if not tags_objs:
                return Response(
                    "Aucun tag correspondant aux références spécifiées n'a été trouvé.",
                    status=status.HTTP_404_NOT_FOUND,
                )

            # Mettre à jour l'emplacement de tous les articles associés aux tags trouvés
            for tag_obj in tags_objs:
                items_objs = item.objects.filter(tag=tag_obj)
                for item_obj in items_objs:
                    old_emplacement = item_obj.emplacement
                    old_departement = item_obj.departement
                    old_personne = item_obj.affectation_personne

                    # Variables pour le nouvel état après mise à jour
                    new_emplacement = old_emplacement
                    new_departement = old_departement
                    new_personne = old_personne

                    if emplacement_id is not None and emplacement_id > 0:
                        emplacement_instance = emplacement.objects.get(
                            pk=emplacement_id
                        )
                        item_obj.emplacement = emplacement_instance
                        new_emplacement = emplacement_instance

                    if departement_id is not None and departement_id > 0:
                        departement_instance = departement.objects.get(
                            pk=departement_id
                        )
                        item_obj.departement = departement_instance
                        new_departement = departement_instance

                    if personne_id is not None and personne_id > 0:
                        personne_instance = Personne.objects.get(pk=personne_id)
                        item_obj.affectation_personne = personne_instance
                        new_personne = personne_instance

                    item_obj.save()

                    # Créer un enregistrement historique même si old et new sont identiques
                    TransferHistorique.objects.create(
                        item_transfer=item_obj,
                        new_emplacement=(
                            new_emplacement
                            if new_emplacement != old_emplacement
                            else None
                        ),
                        old_emplacement=(
                            old_emplacement
                            if new_emplacement != old_emplacement
                            else None
                        ),
                        new_departement=(
                            new_departement
                            if new_departement != old_departement
                            else None
                        ),
                        old_departement=(
                            old_departement
                            if new_departement != old_departement
                            else None
                        ),
                        new_personne=(
                            new_personne if new_personne != old_personne else None
                        ),
                        old_personne=(
                            old_personne if new_personne != old_personne else None
                        ),
                    )

            return Response(
                "L'emplacement des articles a été mis à jour avec succès.",
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            return Response(
                {"error": f"Une erreur s'est produite : {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class TransferHistoriqueListView(ServerSideDataTableView):
    """
    Vue pour lister l'historique des transferts d'un item avec support DataTable
    """
    model = TransferHistorique
    serializer_class = TransferHistoriqueSerializer
    permission_classes = [IsAuthenticated]
    
    # Configuration de l'export
    export_filename = 'transferts_historique'
    
    
    # Configuration DataTable
    search_fields = [
        'item_transfer__article__designation',
        'item_transfer__reference_auto',
        'new_emplacement__nom',
        'old_emplacement__nom',
        'new_departement__nom',
        'old_departement__nom'
    ]
    
    # Mapping des colonnes frontend -> backend
    column_field_mapping = {
        'id': 'id',
        'item_reference': 'item_transfer__reference_auto',
        'item_designation': 'item_transfer__article__designation',
        'new_emplacement': 'new_emplacement__nom',
        'old_emplacement': 'old_emplacement__nom',
        'new_departement': 'new_departement__nom',
        'old_departement': 'old_departement__nom',
        'created_at': 'created_at'
    }

    # Configuration de pagination
    default_page_size = 10
    max_page_size = 100

    def get_queryset(self):
        """Queryset de base - historique d'un item spécifique"""
        item_id = self.kwargs.get('item_transfer')
        
        if not item_id:
            return TransferHistorique.objects.none()
            
        return TransferHistorique.objects.filter(
            item_transfer=item_id
        ).select_related(
            'item_transfer',
            'item_transfer__article',
            'new_emplacement',
            'old_emplacement',
            'new_personne',
            'old_personne',
            'new_departement',
            'old_departement'
        ).order_by("id")


