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
from rest_framework.parsers import MultiPartParser, FormParser
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
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import transaction


class ItemListAPIView(ServerSideDataTableView):
    """
    API ultra-simplifiée pour les items avec support DataTable automatique.
    
    Fonctionnalités automatiques via @datatables/:
    - Pagination côté serveur
    - Recherche globale et par colonnes
    - Tri multi-colonnes
    - Filtres avancés avec mapping automatique
    - Gestion d'erreurs
    - Support DataTable + REST API
    - Export Excel/CSV (activé par défaut)
    """
    model = item
    serializer_class = ItemsSerializer
    permission_classes = [IsAuthenticated]
    # filterset_class = ItemFilter
    
    # Configuration de l'export
    export_filename = 'items'
    
    # Configuration DataTable simple
    search_fields = [
        'reference_auto',
        'numero_serie', 
        'article__designation',
        'article__code_article',
        'emplacement__nom',
        'departement__nom',
        'affectation_personne__nom',
        'affectation_personne__prenom'
    ]
    
    # Mapping des colonnes frontend -> backend
    column_field_mapping = {
        'id': 'id',
        'reference_auto': 'reference_auto',
        'numero_serie': 'numero_serie',
        'article__designation': 'article__designation',  # Support direct du nom de champ
        'article__code_article': 'article__code_article',
        'article__prix_achat': 'article__prix_achat',
        'article__fournisseur': 'article__fournisseur__nom',
        'article__categorie': 'article__produit__categorie__libelle',  # Support pour catégorie
        'article__produit': 'article__produit__libelle',  # Support pour produit/famille
        'article__marque': 'article__marque__nom',  # Support pour marque
        'article__nature': 'article__nature__libelle',  # Support pour nature
        'fournisseur': 'article__fournisseur__nom',  # Alias court pour fournisseur
        'emplacement': 'emplacement__nom',
        'departement': 'departement__nom',
        'statut': 'statut',
        'created_at': 'created_at',
        'date_affectation': 'date_affectation',
        'article_date_achat': 'article__date_achat',
        'article_n_facture': 'article__N_facture',
        # 'affectation_personne_full_name': 'affectation_personne__nom',  # Géré par composite_columns
        'zone': 'emplacement__zone__nom',
        'location': 'emplacement__zone__location__nom',  # Alias pour location
        'valeur_residuelle': 'valeur_residuelle',
        'article_designation': 'article__designation',  # Alias alternatif
        'article_code': 'article__code_article'
    }
    
    # Configuration de pagination
    default_page_size = 20
    max_page_size = 100

    def get_queryset(self):
        """
        Queryset de base avec filtres métier.
        Seuls les items valides non archivés sont retournés.
        """
        if not self.request.user.compte:
            return item.objects.none()
            
        return item.objects.filter(
            article__compte=self.request.user.compte, 
            archive=False
        ).select_related(
            'article',
            'article__produit',
            'article__produit__categorie',
            'article__fournisseur',
            'article__marque',
            'emplacement',
            'emplacement__zone',
            'emplacement__zone__location',
            'departement',
            'affectation_personne',
            'tag'
        ).prefetch_related(
            'archive_items'
        )


class EditItemAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, item_id):
        try:
            item_obj = item.objects.get(
                id=item_id
            )  # Utilise 'Article' avec une majuscule
        except item.DoesNotExist:
            return Response(
                {"message": "item not found"}, status=status.HTTP_404_NOT_FOUND
            )

        serializer = EditItemSerializer(
            item_obj, context={"request": request}
        )  # Passe le contexte
        return Response(serializer.data)


class ItemUpdateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request, item_id, format=None):
        try:
            item_obj = get_object_or_404(article, id=item_id)
        except article.DoesNotExist:
            return Response(
                {"message": "Item not found"}, status=status.HTTP_404_NOT_FOUND
            )

        serializer = UpdateItemArticleSerializer(
            item_obj, data=request.data, partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"message": "Modification réussie", "data": serializer.data},
                status=status.HTTP_200_OK,
            )

        return Response(
            {"message": "Erreur de validation", "errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )


class ArchiveItemListAPIView(ServerSideDataTableView):
    """
    Vue pour lister les items archivés avec support DataTable
    
    Fonctionnalités:
    - Pagination côté serveur
    - Recherche globale et par colonnes
    - Tri multi-colonnes
    - Filtres avancés
    - Export Excel
    """
    model = item
    serializer_class = ItemsSerializer
    permission_classes = [IsAuthenticated]
    
    # Configuration de l'export
    export_filename = 'items_archives'
    
    # Configuration DataTable
    search_fields = [
        'id',
        'reference_auto',
        'numero_serie',
        'article__code_article',
        'departement__nom',
        'article__designation',
        'affectation_personne__prenom',
        'affectation_personne__nom',
        'emplacement__nom',
        'article__fournisseur__nom',
        'article__numero_comptable',
        'article__N_facture',
        'article__produit__libelle',
        'article__produit__categorie__libelle'
    ]
    
    # Mapping des colonnes frontend -> backend
    column_field_mapping = {
        'id': 'id',
        'reference_auto': 'reference_auto',
        'numero_serie': 'numero_serie',
        'article_designation': 'article__designation',
        'article_code_article': 'article__code_article',
        'emplacement': 'emplacement__nom',
        'departement': 'departement__nom',
        'statut': 'statut',
        'created_at': 'created_at',
        'date_affectation': 'date_affectation',
        'article_prix_achat': 'article__prix_achat',
        'article_N_facture': 'article__N_facture'
    }

    # Configuration de pagination
    default_page_size = 20
    max_page_size = 100

    def get_queryset(self):
        """Queryset de base - items archivés uniquement"""
        if not self.request.user.compte:
            return item.objects.none()
            
        return item.objects.filter(
            article__compte=self.request.user.compte,
            archive=True
        ).select_related(
            'article',
            'article__produit',
            'article__produit__categorie',
            'article__fournisseur',
            'article__marque',
            'emplacement',
            'emplacement__zone',
            'departement',
            'affectation_personne',
            'tag'
        ).prefetch_related(
            'archive_items'
        ).order_by("-id")


class ItemDetailsAPI(APIView):
    def get(self, request):
        try:
            user = request.user
            # Récupérer le paramètre de requête 'tag_reference'
            tag_reference = request.query_params.get("tag_reference", None)
            # Filtrer les objets en fonction du tag si 'tag_reference' est fourni
            if tag_reference:
                item_obj = (
                    item.objects.select_related(
                        "article", "tag", "emplacement", "departement"
                    )
                    .filter(tag__reference=tag_reference, tag__compte=user.compte)
                    .first()
                )
                if not item_obj:
                    return Response(
                        {"error": "Aucun élément trouvé pour ce tag."},
                        status=status.HTTP_404_NOT_FOUND,
                    )
            else:
                return Response(
                    {"error": "Veuillez fournir un tag."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Calculate the residual value
            valeur_residuelle = item_obj.calculate_residual_value()

            # Construction de la réponse
            response_data = {
                "id": item_obj.id,
                "statut": item_obj.statut,
                "date_affectation": item_obj.date_affectation,
                "personne": (
                    f"{item_obj.affectation_personne.nom} {item_obj.affectation_personne.prenom}"
                    if item_obj.affectation_personne
                    else None
                ),
                "reference": item_obj.reference_auto,
                "numero_serie": item_obj.numero_serie,
                "departement": (
                    item_obj.departement.nom if item_obj.departement else None
                ),
                "emplacement": (
                    item_obj.emplacement.nom if item_obj.emplacement else None
                ),
                "tag": item_obj.tag.reference if item_obj.tag else None,
                "archive": item_obj.archive,
                "codeArticle": item_obj.article.code_article,
                "designation": item_obj.article.designation,
                "date_achat": item_obj.article.date_achat,
                "date_reception": item_obj.article.date_reception.date(),
                "numero_comptable": item_obj.article.numero_comptable,
                "couleur": item_obj.article.couleur,
                "poids": item_obj.article.poids,
                "volume": item_obj.article.volume,
                "langueur": item_obj.article.langueur,
                "hauteur": item_obj.article.hauteur,
                "largeur": item_obj.article.largeur,
                "date_expiration": item_obj.article.date_expiration,
                "prix_achat": item_obj.article.prix_achat,
                "qte": item_obj.article.qte,
                "n_facture": item_obj.article.N_facture,
                "produit": (
                    item_obj.article.produit.libelle
                    if item_obj.article.produit
                    else None
                ),
                "marque": (
                    item_obj.article.marque.nom if item_obj.article.marque else None
                ),
                "fournisseur": (
                    item_obj.article.fournisseur.nom
                    if item_obj.article.fournisseur
                    else None
                ),
                "nature": (
                    item_obj.article.nature.libelle if item_obj.article.nature else None
                ),
                "categorie": (
                    item_obj.article.produit.categorie.libelle
                    if item_obj.article.produit.categorie
                    else None
                ),
                "valeur_residuelle": valeur_residuelle,
            }

            return Response(response_data, status=status.HTTP_200_OK)

        except item.DoesNotExist:
            return Response(
                {"error": "Aucun élément trouvé pour la référence du tag fournie."},
                status=status.HTTP_404_NOT_FOUND,
            )


class ArchiverItemAPIView(APIView):
    def post(self, request):
        # Données d'entrée
        item_id = request.data.get("id")
        commentaire = request.data.get("commentaire")
        action = request.data.get("action")
        motif = request.data.get("motif")

        # Validation basique
        if not item_id:
            return Response(
                {"error": "id item not provided"}, status=status.HTTP_400_BAD_REQUEST
            )

        if not action:
            return Response(
                {"error": "Action not provided"}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            result = archive_or_unarchive_item_service(
                item_id=int(item_id), action=action, commentaire=commentaire, motif=motif
            )
        except item.DoesNotExist:
            return Response(
                {"error": "Item not found for this id"},
                status=status.HTTP_404_NOT_FOUND,
            )
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:  # noqa: BLE001
            return Response(
                {"error": str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        return Response(
            {
                "message": result.message,
                "already_archived": result.already_archived,
            },
            status=status.HTTP_200_OK,
        )


class ArchiveItemBatchAPIView(APIView):
    """
    API batch pour archiver plusieurs items en une seule requête.

    Body attendu (JSON) :
    {
        "items_id": [1, 2, 3]
    }
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ArchiveItemBatchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        items_id = serializer.validated_data["items_id"]
        motif = serializer.validated_data.get("motif")

        try:
            result = archive_items_batch_service(
                user=request.user,
                items_id=items_id,
                motif=motif,
            )
        except PermissionError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_403_FORBIDDEN)
        except Exception as exc:  # noqa: BLE001
            return Response(
                {"error": str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        return Response(result, status=status.HTTP_200_OK)


class ArchiveItemExcelImportAPIView(APIView):
    """
    API pour importer un fichier Excel et archiver des items en masse.

    Le fichier doit contenir au moins une colonne 'id' (ID de l'item) et
    optionnellement une colonne 'commentaire'.
    """

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        serializer = ArchiveItemExcelImportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        excel_file = serializer.validated_data["file"]
        skip_errors = serializer.validated_data["skip_errors"]

        try:
            result = import_archive_items_from_excel_service(
                user=request.user, excel_file=excel_file, skip_errors=skip_errors
            )
        except ArchiveItemsImportError as exc:
            # Tout ou rien : aucune ligne archivée si des erreurs sont présentes
            return Response({"errors": exc.errors}, status=status.HTTP_400_BAD_REQUEST)
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except PermissionError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_403_FORBIDDEN)
        except Exception as exc:  # noqa: BLE001
            return Response(
                {"error": str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        return Response(result, status=status.HTTP_200_OK)


class AnnulerAffectationAPIView(APIView):
    def post(self, request, item_id):
        try:
            with transaction.atomic():
                # Récupérer l'item
                item_instance = get_object_or_404(item, id=item_id)
                
                # Vérifier s'il y a un tag associé
                if item_instance.tag:
                    tag_instance = item_instance.tag
                    tag_instance.affecter = False
                    tag_instance.save()
                    
                # Mettre à jour la quantité reçue de l'article
                if item_instance.article:
                    item_instance.article.qte_recue = (item_instance.article.qte_recue or 0) + 1
                    item_instance.article.save()

                # Supprimer la relation entre l'item et le tag
                item_instance.tag = None
                item_instance.save()

                # Supprimer l'item
                item_instance.delete()

                return Response({"message": "Affectation annulée avec succès."}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class CountItemPerEmplacement(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, emplacement_id):
        try:
            # Compte les articles pour un emplacement donné
            item_count = item.objects.filter(emplacement__id=emplacement_id).count()
            # Retourne le nombre d'articles dans la réponse
            return Response({"item_count": item_count}, status=status.HTTP_200_OK)
        except item.DoesNotExist:
            # Gérer le cas où l'emplacement n'existe pas
            return Response(
                {"error": "Emplacement non trouvé"}, status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            # Gérer d'autres exceptions générales
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


