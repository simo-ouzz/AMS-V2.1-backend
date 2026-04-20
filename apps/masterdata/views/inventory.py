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
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.contrib.auth.models import Permission
from django.shortcuts import render, redirect
from django.contrib import messages


class InventaireEmplacementListAPIView(ServerSideDataTableView):
    """
    Vue pour lister les inventaires d'emplacement avec support DataTable
    
    Fonctionnalités automatiques via @datatables/:
    - Pagination côté serveur
    - Recherche globale et par colonnes
    - Tri multi-colonnes
    - Filtres avancés avec mapping automatique
    - Gestion d'erreurs
    - Support DataTable + REST API
    """
    model = inventaire
    serializer_class = InventaireSerializer
    permission_classes = [IsAuthenticated]
    
    # Configuration de l'export
    export_filename = 'inventaires_emplacement'
    
    # Configuration DataTable
    search_fields = [
        'nom',
        'reference', 
        'inventaire_emplacement_set__emplacement__nom',
        'user__username',
        'created_at',
        'departement__nom'
    ]
    
    # Mapping des colonnes frontend -> backend
    column_field_mapping = {
        'id': 'id',
        'nom': 'nom',
        'reference': 'reference',
        'emplacement': 'inventaire_emplacement_set__emplacement__nom',
        'emplacement_nom': 'inventaire_emplacement_set__emplacement__nom',
        'user': 'user__username',
        'user_nom': 'user__first_name',
        'user_prenom': 'user__last_name',
        'date_creation': 'created_at',
        'statut': 'statut',
        'categorie': 'categorie',
        'departement': 'departement__nom'
    }

    # Configuration de pagination
    default_page_size = 20
    max_page_size = 100

    def get_queryset(self):
        """
        Queryset de base avec filtres métier.
        Seuls les inventaires d'emplacement valides sont retournés.
        """
        if not self.request.user.compte:
            return inventaire.objects.none()
        
        return inventaire.objects.filter(
            user__compte=self.request.user.compte, 
            categorie="Emplacement"
        ).select_related(
            'user',
            'departement'
        ).prefetch_related(
            'inventaire_emplacement_set',
            'inventaire_emplacement_set__emplacement'
        ).order_by("-id")

    # DataTable2 s'occupe de la sérialisation et de la pagination avec InventaireSerializer


class InventaireEmplacementListMobileAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            user = request.user
            if not user.compte:
                return Response(
                    {"error": "User does not have an associated account"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            emp_qs = (
                inventaire_emplacement.objects.filter(
                    inventaire__user__compte=user.compte,
                    start_at=True,
                )
                .exclude(statut="Terminer")
                .select_related(
                    "inventaire",
                    "inventaire__user",
                    "emplacement",
                    "affceted_at",
                )
                .distinct()
            )

            serialized_data = [
                {
                    "id": emp.id,
                    "inventaireId": emp.inventaire.id,
                    "categorie": emp.inventaire.categorie,
                    "affceted_at": emp.affceted_at_id,
                    "emplacementId": emp.emplacement.id,
                    "operateur": (
                        f"{emp.affceted_at.nom} {emp.affceted_at.prenom}"
                        if emp.affceted_at
                        else None
                    ),
                    "nom": emp.inventaire.nom,
                    "reference": emp.inventaire.reference,
                    "emplacement_nom": emp.emplacement.nom,
                    "user": f"{emp.inventaire.user.nom} {emp.inventaire.user.prenom}",
                    "created_at": emp.created_at,
                    "statut": emp.statut,
                }
                for emp in emp_qs
            ]

            return Response(serialized_data, status=status.HTTP_200_OK)

        except inventaire.DoesNotExist:
            return Response(
                {"error": "Inventaire not found"}, status=status.HTTP_404_NOT_FOUND
            )

        except UserWeb.DoesNotExist:
            return Response(
                {"error": "User not found"}, status=status.HTTP_404_NOT_FOUND
            )

        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


from openpyxl import Workbook



class InventaireEmplacementCreateAPIView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        nom = request.data.get("nom")
        emplacement_id = request.data.get("emplacement_id")
        date_creation = request.data.get("date_creation")
        if not (nom and emplacement_id):
            return Response(
                {"message": "Tous les champs sont requis"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            emplacement_instance = emplacement.objects.get(pk=emplacement_id)
        except emplacement.DoesNotExist:
            return Response(
                {"message": "L'emplacement spécifié n'existe pas"},
                status=status.HTTP_404_NOT_FOUND,
            )

        user_instance = request.user  # Récupérer l'utilisateur à partir du jeton JWT

        inventaire_instance = inventaire.objects.create(
            nom=nom,
            user=user_instance,
            date_creation=date_creation,
            categorie="Emplacement",
        )
        inventaire_emplacement.objects.create(
            inventaire=inventaire_instance, emplacement=emplacement_instance
        )

        return Response(
            {"message": "Inventaire créé avec succès"}, status=status.HTTP_201_CREATED
        )


class InventaireEmplacementDetailAPIView(ServerSideDataTableView):
    """
    Vue pour lister les emplacements d'un inventaire avec support DataTable
    Retourne les détails de l'inventaire et la liste des emplacements associés
    """
    model = inventaire_emplacement
    serializer_class = InventaireEmplacementSimpleSerializer
    permission_classes = [IsAuthenticated]
    
    # Configuration de l'export
    export_filename = 'inventaire_emplacements_detail'
    
    
    # Configuration DataTable
    search_fields = [
        'emplacement__nom',
        'emplacement__id',
        'statut'
    ]
    
    # Mapping des colonnes frontend -> backend
    column_field_mapping = {
        'id': 'id',
        'emplacement': 'emplacement__nom',
        'emplacement_id': 'emplacement__id',
        'statut': 'statut',
        'created_at': 'created_at'
    }

    # Configuration de pagination
    default_page_size = 100
    max_page_size = 1000

    def get_queryset(self):
        """
        Queryset de base filtré par inventaire_id.
        """
        inventaire_id = self.kwargs.get('inventaire_id')

        if not self.request.user.compte:
            return inventaire_emplacement.objects.none()

        try:
            inventaire_instance = inventaire.objects.get(
                id=inventaire_id,
                user__compte=self.request.user.compte
            )
        except inventaire.DoesNotExist:
            return inventaire_emplacement.objects.none()

        return inventaire_emplacement.objects.filter(
            inventaire=inventaire_instance
        ).select_related(
            'emplacement',
            'inventaire'
        ).order_by("id")

    def get(self, request, inventaire_id, *args, **kwargs):
        """Override pour ajouter les infos de l'inventaire dans la réponse"""
        self.kwargs['inventaire_id'] = inventaire_id
        
        # Récupérer les infos de l'inventaire
        try:
            inventaire_instance = inventaire.objects.get(
                id=inventaire_id, 
                user__compte=request.user.compte
            )
            inventaire_data = {
                "id": inventaire_instance.id,
                "nom": inventaire_instance.nom,
                "reference": inventaire_instance.reference,
                "date_creation": inventaire_instance.date_creation,
            }
            
            # Récupérer les IDs des emplacements
            emplacements = inventaire_emplacement.objects.filter(
                inventaire=inventaire_instance
            )
            emplacement_ids = [emp.emplacement.id for emp in emplacements]
            
        except inventaire.DoesNotExist:
            return Response(
                {"message": "Inventaire non trouvé"}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Traitement DataTable standard
        response = super().get(request, *args, **kwargs)
        
        # Ajouter les infos de l'inventaire à la réponse
        if isinstance(response, Response):
            response.data['inventaire'] = inventaire_data
            response.data['emplacements'] = emplacement_ids
        
        return response


class InventaireEmplacementUpdateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request, inventaire_id):
        try:
            inventaire_instance = inventaire.objects.get(id=inventaire_id)
        except inventaire.DoesNotExist:
            return Response(
                {"message": "Inventaire non trouvé"}, status=status.HTTP_404_NOT_FOUND
            )

        serializer = InventaireSerializer(
            inventaire_instance, data=request.data, partial=True
        )
        if serializer.is_valid():
            serializer.save()

            # Update entries in the pivot table
            emplacements_data = request.data.get(
                "emplacement_id"
            )  # Assuming emplacements are sent in the appropriate format
            inventaire_emplacement.objects.filter(
                inventaire=inventaire_instance
            ).delete()

            try:
                emplacement_instance = emplacement.objects.get(id=emplacements_data)
                inventaire_emplacement.objects.create(
                    inventaire=inventaire_instance, emplacement=emplacement_instance
                )
            except emplacement.DoesNotExist:
                return Response(
                    {
                        "message": f"Emplacement avec l'ID {emplacements_data} non trouvé"
                    },
                    status=status.HTTP_404_NOT_FOUND,
                )

            return Response(serializer.data)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class InventaireEmplacementsDetailAPIView(ServerSideDataTableView):
    """
    Vue pour lister les détails des emplacements d'un inventaire avec support DataTable
    """
    model = inventaire_emplacement
    serializer_class = InventaireEmplacementDetailSerializer
    permission_classes = [IsAuthenticated]
    
    # Configuration de l'export
    export_filename = 'inventaire_details_operateurs'
    
    
    # Configuration DataTable
    search_fields = [
        'emplacement__nom',
        'emplacement__id',
        'affceted_at__nom',
        'affceted_at__prenom',
        'statut'
    ]
    
    # Mapping des colonnes frontend -> backend
    column_field_mapping = {
        'id': 'id',
        'emplacement': 'emplacement__nom',
        'emplacement_nom': 'emplacement__nom',
        'operateur': 'affceted_at__nom',
        'operateur_nom': 'affceted_at__nom',
        'operateur_prenom': 'affceted_at__prenom',
        'statut': 'statut',
        'etat': 'start_at',
        'created_at': 'created_at'
    }

    # Configuration de pagination
    default_page_size = 20
    max_page_size = 100

    def get_queryset(self):
        """
        Queryset de base filtré par inventaire_id.
        """
        inventaire_id = self.kwargs.get('inventaire_id')
        
        if not self.request.user.compte:
            return inventaire_emplacement.objects.none()
        
        # Vérifier que l'inventaire appartient au compte de l'utilisateur
        try:
            inventaire_instance = inventaire.objects.get(
                id=inventaire_id, 
                user__compte=self.request.user.compte
            )
        except inventaire.DoesNotExist:
            return inventaire_emplacement.objects.none()
            
        return inventaire_emplacement.objects.filter(
            inventaire=inventaire_instance
        ).select_related(
            'emplacement',
            'affceted_at',
            'inventaire'
        ).order_by("-id")
    
    def get(self, request, inventaire_id, *args, **kwargs):
        """Override pour ajouter les infos de l'inventaire dans la réponse"""
        self.kwargs['inventaire_id'] = inventaire_id
        
        # Récupérer les infos de l'inventaire
        try:
            inventaire_instance = inventaire.objects.get(
                id=inventaire_id, 
                user__compte=request.user.compte
            )
            inventaire_data = {
                "id": inventaire_instance.id,
                "nom": inventaire_instance.nom,
                "reference": inventaire_instance.reference,
                "date_creation": inventaire_instance.date_creation,
                "statut": inventaire_instance.statut,
            }
        except inventaire.DoesNotExist:
            return Response(
                {"message": "Inventaire non trouvé"}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Traitement DataTable standard
        response = super().get(request, *args, **kwargs)
        
        # Ajouter les infos de l'inventaire à la réponse
        if isinstance(response, Response):
            response.data['result'] = inventaire_data
        
        return response


from rest_framework.exceptions import NotFound


class InfoInventaire(generics.ListAPIView):
    def get(self, request, inventaire_id):
        try:
            # Assurez-vous que l'objet 'inventaire' existe pour l'utilisateur
            inventaire_instance = inventaire.objects.get(
                id=inventaire_id, user__compte=request.user.compte
            )

            # Structure des données à renvoyer
            inventaire_data = {
                "id": inventaire_instance.id,
                "nom": inventaire_instance.nom,
                "reference": inventaire_instance.reference,
                "date_creation": inventaire_instance.date_creation,
                "statut": inventaire_instance.statut,
            }

            # Retourner la réponse sous forme de JSON
            return Response(inventaire_data)

        except inventaire.DoesNotExist:
            # Si l'objet 'Inventaire' n'existe pas pour cet utilisateur
            raise NotFound(
                detail="Inventaire non trouvé ou vous n'avez pas accès à cet inventaire."
            )

        except Exception as e:
            # Pour toute autre erreur générale (ex: erreur de connexion DB)
            return Response(
                {"error": str(e)},
                status=500,  # Code de statut 500 pour une erreur serveur
            )


# inventaire par zone


class InventaireZoneListsAPIView(ServerSideDataTableView):
    """
    Vue pour lister les inventaires de zone avec support DataTable
    
    Fonctionnalités automatiques via @datatables/:
    - Pagination côté serveur
    - Recherche globale et par colonnes
    - Tri multi-colonnes
    - Filtres avancés avec mapping automatique
    - Gestion d'erreurs
    - Support DataTable + REST API
    """
    model = inventaire
    serializer_class = InventaireZoneSerializer
    permission_classes = [IsAuthenticated]
    
    # Configuration de l'export
    export_filename = 'inventaires_zone'
    
    
    # Configuration DataTable
    search_fields = [
        'nom',
        'reference',
        'inventaire_emplacement_set__emplacement__zone__nom',
        'user__username',
        'created_at',
        'departement__nom'
    ]
    
    # Mapping des colonnes frontend -> backend
    column_field_mapping = {
        'id': 'id',
        'nom': 'nom',
        'reference': 'reference',
        'zone': 'inventaire_emplacement_set__emplacement__zone__nom',
        'zone_nom': 'inventaire_emplacement_set__emplacement__zone__nom',
        'user': 'user__username',
        'user_nom': 'user__first_name',
        'user_prenom': 'user__last_name',
        'created_at': 'created_at',
        'updated_at': 'updated_at',
        'statut': 'statut',
        'categorie': 'categorie',
        'departement': 'departement__nom'
    }

    # Configuration de pagination
    default_page_size = 20
    max_page_size = 100

    def get_queryset(self):
        """
        Queryset de base avec filtres métier.
        Seuls les inventaires de zone valides sont retournés.
        """
        if not self.request.user.compte:
            return inventaire.objects.none()
            
        return inventaire.objects.filter(
            user__compte=self.request.user.compte, 
            categorie="Zone"
        ).select_related(
            'user',
            'departement'
        ).prefetch_related(
            'inventaire_emplacement_set',
            'inventaire_emplacement_set__emplacement',
            'inventaire_emplacement_set__emplacement__zone'
        ).order_by("-id")


class InventaireZoneCreateAPIView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        nom = request.data.get("nom")
        zone_id = request.data.get("zone_id")
        date_creation = request.data.get("date_creation")

        if not (nom and zone_id and date_creation):
            return Response(
                {"message": "Tous les champs sont requis"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            zone_instance = zone.objects.get(pk=zone_id)
        except zone.DoesNotExist:
            return Response(
                {"message": "La zone spécifiée n'existe pas"},
                status=status.HTTP_404_NOT_FOUND,
            )

        user_instance = request.user

        # Créer l'inventaire
        inventaire_instance = inventaire.objects.create(
            nom=nom,
            user=user_instance,
            date_creation=date_creation,
            categorie="Zone",
        )

        # Récupérer les emplacements associés à la zone et créer les entrées d'inventaire_emplacement
        emplacements = emplacement.objects.filter(zone=zone_instance)
        for emplacement_instance in emplacements:
            inventaire_emplacement.objects.create(
                inventaire=inventaire_instance, emplacement=emplacement_instance
            )

        return Response(
            {"message": "Inventaire créé avec succès"}, status=status.HTTP_201_CREATED
        )


class InventaireZoneDetailsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, inventaire_id):
        try:
            # Récupérer l'inventaire
            inventaire_instance = inventaire.objects.get(id=inventaire_id)
        except inventaire.DoesNotExist:
            return Response(
                {"message": "L'inventaire spécifié n'existe pas"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Récupérer les emplacements associés à l'inventaire à partir de la table pivot
        emplacements = inventaire_emplacement.objects.filter(
            inventaire=inventaire_instance
        ).select_related("emplacement")

        # Extraire la zone de chaque emplacement
        zones = set(emplacements.values_list("emplacement__zone__id", flat=True))

        # Sérialiser les données
        data = {
            "inventaire": {
                "id": inventaire_instance.id,
                "nom": inventaire_instance.nom,
                "reference": inventaire_instance.reference,
                "date_creation": inventaire_instance.date_creation,
                # Ajoutez d'autres champs de l'inventaire si nécessaire
            },
            "zone": list(
                zones
            ),  # Convertir l'ensemble de zones en liste pour la réponse JSON
        }

        return Response(data)


class InventaireZoneUpdatesAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request, inventaire_id):
        try:
            # Récupérer l'inventaire
            inventaire_instance = inventaire.objects.get(id=inventaire_id)
        except inventaire.DoesNotExist:
            return Response(
                {"message": "L'inventaire spécifié n'existe pas"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Récupérer les données de la requête
        nom = request.data.get("nom")
        zone_id = request.data.get("zone_id")

        # Vérifier si toutes les données requises sont présentes
        if not (nom and zone_id):
            return Response(
                {"message": "Tous les champs sont requis"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            # Récupérer la zone spécifiée
            zone_instance = zone.objects.get(pk=zone_id)
        except zone.DoesNotExist:
            return Response(
                {"message": "La zone spécifiée n'existe pas"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Modifier les champs de l'inventaire
        inventaire_instance.nom = nom
        # Modifier d'autres champs de l'inventaire si nécessaire
        inventaire_instance.save()

        # Modifier les emplacements associés à l'inventaire en fonction de la nouvelle zone
        emplacements = emplacement.objects.filter(zone=zone_instance)

        # Effacer les anciens emplacements associés à l'inventaire
        inventaire_emplacement.objects.filter(inventaire=inventaire_instance).delete()

        # Ajouter les nouveaux emplacements associés à la nouvelle zone
        for emplacement_instance in emplacements:
            inventaire_emplacement.objects.create(
                inventaire=inventaire_instance, emplacement=emplacement_instance
            )

        return Response(
            {"message": "Inventaire modifié avec succès"}, status=status.HTTP_200_OK
        )


# inventaire par location


class InventaireLocationListsAPIView(ServerSideDataTableView):
    """
    Vue pour lister les inventaires de location avec support DataTable
    
    Fonctionnalités automatiques via @datatables/:
    - Pagination côté serveur
    - Recherche globale et par colonnes
    - Tri multi-colonnes
    - Filtres avancés avec mapping automatique
    - Gestion d'erreurs
    - Support DataTable + REST API
    """
    model = inventaire
    serializer_class = InventaireLocationSerializer
    permission_classes = [IsAuthenticated]
    
    # Configuration de l'export
    export_filename = 'inventaires_location'
    
    # Configuration DataTable
    search_fields = [
        'nom',
        'reference',
        'inventaire_emplacement_set__emplacement__zone__location__nom',
        'user__username',
        'created_at',
        'departement__nom'
    ]
    
    # Mapping des colonnes frontend -> backend
    column_field_mapping = {
        'id': 'id',
        'nom': 'nom',
        'reference': 'reference',
        'location': 'inventaire_emplacement_set__emplacement__zone__location__nom',
        'location_nom': 'inventaire_emplacement_set__emplacement__zone__location__nom',
        'user': 'user__username',
        'user_nom': 'user__first_name',
        'user_prenom': 'user__last_name',
        'created_at': 'created_at',
        'updated_at': 'updated_at',
        'statut': 'statut',
    }

    # Configuration de pagination
    default_page_size = 20
    max_page_size = 100

    def get_queryset(self):
        """
        Queryset de base avec filtres métier.
        Seuls les inventaires de location valides sont retournés.
        """
        if not self.request.user.compte:
            return inventaire.objects.none()
            
        return inventaire.objects.filter(
            user__compte=self.request.user.compte, 
            categorie="Location"
        ).select_related(
            'user',
            'departement'
        ).prefetch_related(
            'inventaire_emplacement_set',
            'inventaire_emplacement_set__emplacement',
            'inventaire_emplacement_set__emplacement__zone',
            'inventaire_emplacement_set__emplacement__zone__location'
        ).order_by("-id")


class InventaireLocationCreateAPIView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        nom = request.data.get("nom")
        location_id = request.data.get("location_id")  # Retirer la virgule ici
        date_creation = request.data.get("date_creation")

        if not (nom and location_id):
            return Response(
                {"message": "Tous les champs sont requis"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            location_instance = location.objects.get(pk=location_id)
        except location.DoesNotExist:
            return Response(
                {"message": "La location spécifiée n'existe pas"},
                status=status.HTTP_404_NOT_FOUND,
            )

        user_instance = request.user

        # Récupérer tous les emplacements associés à la location spécifiée
        emplacements = emplacement.objects.filter(zone__location=location_instance)

        inventaire_instance = inventaire.objects.create(
            nom=nom,
            user=user_instance,
            date_creation=date_creation,
            categorie="Location",
        )

        for emplacement_instance in emplacements:
            inventaire_emplacement.objects.create(
                inventaire=inventaire_instance, emplacement=emplacement_instance
            )

        return Response(
            {"message": "Inventaire créé avec succès"}, status=status.HTTP_201_CREATED
        )


class InventaireLocationDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, inventaire_id):
        try:
            # Récupérer l'inventaire
            inventaire_obj = inventaire.objects.get(pk=inventaire_id)

            # Obtenir tous les emplacements associés à cet inventaire
            emplacements = inventaire_emplacement.objects.filter(
                inventaire=inventaire_obj
            )

            # Récupérer les zones uniques des emplacements
            zones = emplacements.values_list("emplacement__zone", flat=True).distinct()

            # Récupérer les locations correspondant à ces zones
            locations = location.objects.filter(zone__in=zones)

            # Sélectionner une seule location si disponible
            location_ids = []
            if locations.exists():
                location_ids.append(locations.first().id)

            # Sérialiser les données de l'inventaire
            inventaire_serializer = InventaireSerializer(inventaire_obj)

            # Construire la réponse avec l'inventaire et les identifiants de location
            response_data = {
                "inventaire": inventaire_serializer.data,
                "location": location_ids,
            }

            return Response(response_data, status=status.HTTP_200_OK)
        except inventaire.DoesNotExist:
            return Response(
                {"message": "Inventaire non trouvé"}, status=status.HTTP_404_NOT_FOUND
            )


class InventaireLocationUpdateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request, inventaire_id):
        try:
            # Récupérer l'inventaire
            inventaire_instance = inventaire.objects.get(id=inventaire_id)
        except inventaire.DoesNotExist:
            return Response(
                {"message": "Inventaire non trouvé"}, status=status.HTTP_404_NOT_FOUND
            )

        # Mettre à jour les champs de l'inventaire avec les données fournies
        nom = request.data.get("nom", inventaire_instance.nom)
        statut = request.data.get("statut", inventaire_instance.statut)

        # Appliquer les modifications
        inventaire_instance.nom = nom
        inventaire_instance.statut = statut

        # Récupérer l'ID de la nouvelle location sélectionnée, si fourni
        new_location_id = request.data.get("location_id")
        if new_location_id:
            # Vérifier si la nouvelle location est valide
            try:
                new_location = location.objects.get(id=new_location_id)
                # Récupérer tous les emplacements associés à la nouvelle location
                new_location_emplacements = emplacement.objects.filter(
                    zone__location=new_location
                )

                # Supprimer tous les emplacements existants associés à l'inventaire
                inventaire_emplacement.objects.filter(
                    inventaire=inventaire_instance
                ).delete()

                # Associer les nouveaux emplacements à l'inventaire
                for emplacement_instance in new_location_emplacements:
                    inventaire_emplacement.objects.create(
                        inventaire=inventaire_instance, emplacement=emplacement_instance
                    )
            except location.DoesNotExist:
                return Response(
                    {"message": "La nouvelle location spécifiée est invalide"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # Enregistrer les modifications de l'inventaire
        inventaire_instance.save()

        return Response(
            {"message": "Inventaire et emplacements modifiés avec succès"},
            status=status.HTTP_200_OK,
        )


# inventaire par departement


class InventaireDepartementListAPIView(ServerSideDataTableView):
    """
    Vue pour lister les inventaires de département avec support DataTable
    """
    model = inventaire
    serializer_class = InventaireDepartementSerializer
    permission_classes = [IsAuthenticated]
    
    # Configuration de l'export
    export_filename = 'inventaires_departement'
    
    # Configuration DataTable
    search_fields = [
        'nom',
        'reference',
        'user__username',
        'created_at',
        'departement__nom'
    ]
    
    # Mapping des colonnes frontend -> backend
    column_field_mapping = {
        'id': 'id',
        'nom': 'nom',
        'reference': 'reference',
        'user': 'user__username',
        'created_at': 'created_at',
        'statut': 'statut',
        'categorie': 'categorie',
        'departement': 'departement__nom'
    }

    # Configuration de pagination
    default_page_size = 20
    max_page_size = 100

    def get_queryset(self):
        """
        Queryset de base avec filtres métier.
        Seuls les inventaires de département valides sont retournés.
        """
        if not self.request.user.compte:
            return inventaire.objects.none()
            
        return inventaire.objects.filter(
            user__compte=self.request.user.compte, 
            categorie="Departement"
        ).select_related(
            'user',
            'departement'
        ).prefetch_related(
            'inventaire_emplacement_set',
            'inventaire_emplacement_set__emplacement'
        ).order_by("-id")


class InventaireCreateByDepartementAPIView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        nom = request.data.get("nom")
        date_creation = request.data.get("date_creation")
        departement_id = request.data.get("departement_id")  # Un seul ID

        if not (nom and departement_id):
            return Response(
                {"message": "Tous les champs sont requis"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            # Récupérer l'utilisateur (dans cet exemple, l'utilisateur est statiquement choisi)
            user_instance = request.user
            departement_instance = departement.objects.filter(id=departement_id).first()

            # Créer l'inventaire
            inventaire_instance = inventaire.objects.create(
                nom=nom,
                user=user_instance,
                date_creation=date_creation,
                statut="En attente",
                categorie="Departement",
                departement=departement_instance,
            )

            # Trouver les articles associés au département spécifié
            items_associes = item.objects.filter(departement_id=departement_id)

            # Grouper les articles par emplacement
            emplacements_vus = set()  # Pour éviter les duplications
            for art in items_associes:
                emplacement_instance = art.emplacement
                if emplacement_instance not in emplacements_vus:
                    # Créer un inventaire_emplacement uniquement pour les emplacements uniques
                    inventaire_emplacement.objects.create(
                        emplacement=emplacement_instance,
                        inventaire=inventaire_instance,
                        statut="en attente",
                    )
                    emplacements_vus.add(emplacement_instance)

            # Utiliser le sérialiseur pour obtenir les données de l'inventaire
            serializer = InventaireSerializer(inventaire_instance)

            response_data = {
                "inventaire": serializer.data,
                "departements": [
                    departement_id
                ],  # Retourner comme une liste avec un seul élément
            }

            return Response(response_data, status=status.HTTP_201_CREATED)

        except item.DoesNotExist:
            return Response(
                {"message": "Le département spécifié n'existe pas"},
                status=status.HTTP_404_NOT_FOUND,
            )


class InventaireDepartementDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, inventaire_id):
        try:
            # Récupérer l'inventaire
            inventaire_instance = inventaire.objects.get(id=inventaire_id)

            # Sérialiser l'inventaire
            serializer = InventaireSerializer(inventaire_instance)

            # Récupérer le premier département associé à cet inventaire
            inventaire_emplacements = inventaire_emplacement.objects.filter(
                inventaire=inventaire_instance
            )
            department_id = None
            for ie in inventaire_emplacements:
                items = item.objects.filter(emplacement=ie.emplacement)
                for art in items:
                    department_id = art.departement.id
                    break
                if department_id is not None:
                    break

            # Ajouter le département à la réponse
            response_data = {
                "inventaire": serializer.data,
                "departements": [department_id] if department_id is not None else [],
            }

            return Response(response_data)
        except inventaire.DoesNotExist:
            return Response(
                {"message": "Inventaire non trouvé"}, status=status.HTTP_404_NOT_FOUND
            )


class InventaireDepartementUpdateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request, inventaire_id):
        try:
            # Récupérer l'inventaire à modifier
            inventaire_instance = inventaire.objects.get(id=inventaire_id)

            # Vos modifications à l'inventaire
            inventaire_instance.nom = request.data.get("nom", inventaire_instance.nom)
            # inventaire_instance.reference = request.data.get(
            #     "reference", inventaire_instance.reference
            # )

            # Sauvegarder les modifications de l'inventaire
            inventaire_instance.save()

            # Récupérer l'ID du département à associer (s'il est fourni dans la requête)
            departement_id = request.data.get("departement_id")

            # Vérifier si un département a été sélectionné
            try:
                # Récupérer le département sélectionné
                departement_instance = departement.objects.get(id=departement_id)

                # Effacer les anciens emplacements associés à cet inventaire
                inventaire_emplacement.objects.filter(
                    inventaire=inventaire_instance
                ).delete()

                # Récupérer les emplacements associés au département sélectionné
                items = item.objects.filter(departement=departement_instance)
                for art in items:
                    # Créer de nouveaux emplacements pour cet inventaire
                    inventaire_emplacement.objects.create(
                        inventaire=inventaire_instance, emplacement=art.emplacement
                    )

                # Mettre à jour l'inventaire avec le nouveau département
                inventaire_instance.save()

                return Response(
                    {"message": "Inventaire et emplacements modifiés avec succès"},
                    status=status.HTTP_200_OK,
                )
            except departement.DoesNotExist:
                return Response(
                    {"message": "Le département spécifié n'existe pas"},
                    status=status.HTTP_404_NOT_FOUND,
                )

        except inventaire.DoesNotExist:
            return Response(
                {"message": "Inventaire non trouvé"}, status=status.HTTP_404_NOT_FOUND
            )


# Affectation
from django.shortcuts import get_object_or_404

from django.db.models import F
from django.http import JsonResponse


from masterdata.models import emplacement

from django.core.exceptions import ObjectDoesNotExist

from django.db import transaction  # Importez la transaction

from rest_framework import status


def verifier_tags(liste_references_tags, user):
    known_tags = tag.objects.filter(
        reference__in=liste_references_tags, compte=user.compte
    )
    known_refs = {t.reference for t in known_tags}
    tags_connus = list(known_tags)
    tags_inconnus = [r for r in liste_references_tags if r not in known_refs]
    return tags_connus, tags_inconnus


def verifier_tags_affecter(liste_references_tags, user):
    # Si la liste contient des chaînes, convertir en objets `tag`
    if all(isinstance(tag_obj, str) for tag_obj in liste_references_tags):
        tags = tag.objects.filter(
            reference__in=liste_references_tags, compte=user.compte
        )
    elif all(isinstance(tag_obj, tag) for tag_obj in liste_references_tags):
        tags = liste_references_tags
    else:
        raise ValueError(
            "La liste doit contenir uniquement des chaînes de caractères ou des objets tag."
        )

    tags_affectes = []
    tags_non_affectes = []

    # Parcourir les tags et les classer en affectés ou non-affectés
    for tag_obj in tags:
        if tag_obj.affecter:
            tags_affectes.append(tag_obj)
        else:
            tags_non_affectes.append(tag_obj)

    return tags_affectes, tags_non_affectes


def verifier_emplacement_tags(tags_references, emplacement_id, user):
    bons_emplacements = []
    mauvais_emplacements = []

    tags_affectes, _ = verifier_tags_affecter(tags_references, user)
    for tag_obj in tags_affectes:
        item_obj = item.objects.filter(
            tag=tag_obj, article__compte=user.compte, archive=False
        ).first()
        if item_obj:
            if item_obj.emplacement_id == emplacement_id:
                bons_emplacements.append(tag_obj)
            else:
                mauvais_emplacements.append(tag_obj)
        else:
            mauvais_emplacements.append(tag_obj)

    return bons_emplacements, mauvais_emplacements


def verifier_tags_manquants(references_tags, id_emplacement):
    items = item.objects.filter(emplacement_id=id_emplacement, archive=False).select_related("tag")

    tags_trouvables = []
    tags_manquants = []

    for item_obj in items:
        if item_obj.tag:
            if item_obj.tag.reference in references_tags:
                tags_trouvables.append(item_obj.tag.reference)
            else:
                tags_manquants.append(item_obj.tag.reference)
        else:
            tags_manquants.append(
                "Aucun tag associé à l'article {}".format(item_obj.numero_serie)
            )

    return tags_trouvables, tags_manquants


def verifier_items_archives(tags_references, emplacement_id, user):
    items_archives = []

    tags_affectes, _ = verifier_tags_affecter(tags_references, user)

    for tag_obj in tags_affectes:
        item_obj = item.objects.filter(
            tag=tag_obj, article__compte=user.compte, archive=True
        ).first()

        if item_obj and item_obj.emplacement_id == emplacement_id:
            items_archives.append(item_obj.tag.reference)

    return items_archives


def filter_tags_by_emplacement_and_departement(
    tags_references, emplacement_id, departement_id
):
    try:
        items_in_emplacement = item.objects.filter(
            tag__reference__in=tags_references,
            emplacement_id=emplacement_id,
            archive=False,
        )
        items_in_department = items_in_emplacement.filter(departement_id=departement_id)

        filtered_tags = items_in_department.values_list("tag__reference", flat=True)
        return list(filtered_tags)

    except Exception as e:
        return {"error": f"Une erreur est survenue : {str(e)}"}


class VerifyTagsLocationAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = request.data
        user = request.user
        tags_references = data.get("tags", [])
        emplacement_id = data.get("emplacement_id")
        inventaire_id = data.get("inventaire_id")

        if not tags_references or not emplacement_id or not inventaire_id:
            return Response(
                {"error": "Tous les champs requis ne sont pas fournis."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        emplacement_instance = emplacement.objects.filter(id=emplacement_id).first()
        if not emplacement_instance:
            return Response(
                {"error": "Emplacement introuvable."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        inventaire_instance = inventaire.objects.filter(pk=inventaire_id).first()
        if not inventaire_instance:
            return Response(
                {"error": "Inventaire introuvable."}, status=status.HTTP_400_BAD_REQUEST
            )

        # Vérifier que l'emplacement fait partie de la campagne
        if not inventaire_emplacement.objects.filter(
            inventaire=inventaire_instance, emplacement=emplacement_instance
        ).exists():
            return Response(
                {"error": "Cet emplacement ne fait pas partie de cette campagne."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Récupérer tous les tags du compte utilisateur
        tags_queryset = tag.objects.filter(
            reference__in=tags_references, compte=user.compte
        )
        
        # Filtrer par département si nécessaire
        tags_references_filtered = tags_references
        if inventaire_instance.departement is not None:
            filtered_result = filter_tags_by_emplacement_and_departement(
                tags_references,
                emplacement_instance.id,
                inventaire_instance.departement.id,
            )
            # Vérifier si le résultat est une liste ou un dictionnaire d'erreur
            if isinstance(filtered_result, list):
                tags_references_filtered = filtered_result
            else:
                # En cas d'erreur, utiliser toutes les références
                tags_references_filtered = tags_references

        # Identifier les tags inconnus (qui n'existent pas dans la base)
        tags_inconnus = [
            ref
            for ref in tags_references
            if ref not in tags_queryset.values_list("reference", flat=True)
        ]

        # Utiliser les références filtrées pour les vérifications
        tags_references_to_check = tags_references_filtered
        
        # Vérifier les tags affectés/non affectés
        tags_affectes, tags_non_affectes = verifier_tags_affecter(
            tags_references_to_check, user
        )
        
        # Vérifier les emplacements
        bons_emplacements, mauvais_emplacements = verifier_emplacement_tags(
            tags_references_to_check, emplacement_instance.id, user
        )
        
        # Vérifier les items archivés
        item_archive = verifier_items_archives(
            tags_references_to_check, emplacement_instance.id, user
        )
        
        # Vérifier les tags manquants (items dans l'emplacement non scannés)
        tags_trouvables, tags_manquants = verifier_tags_manquants(
            tags_references_to_check, emplacement_instance.id
        )

        response_data = []
        counts = {
            "trouvee": 0,
            "inconnu": 0,
            "manquant": 0,
            "non_affecter": 0,
            "intru": 0,
        }

        # Traiter les tags avec bon emplacement (trouvee)
        for tag_obj in bons_emplacements:
            if isinstance(tag_obj, tag):
                item_obj_correct = item.objects.filter(
                    tag=tag_obj, archive=False
                ).first()
                if item_obj_correct:
                    response_data.append(
                        self.format_response(
                            item_obj_correct, tag_obj.reference, "trouvee"
                        )
                    )
                    counts["trouvee"] += 1

        # Traiter les tags avec mauvais emplacement (intru)
        for tag_obj in mauvais_emplacements:
            if isinstance(tag_obj, tag):
                item_obj_intru = item.objects.filter(tag=tag_obj, archive=False).first()
                if item_obj_intru:
                    response_data.append(
                        self.format_response(item_obj_intru, tag_obj.reference, "intru")
                    )
                    counts["intru"] += 1

        # Traiter les tags inconnus
        for tag_reference in tags_inconnus:
            response_data.append({"tag": tag_reference, "statut": "inconnu"})
            counts["inconnu"] += 1

        # Traiter les tags non affectés
        for tag_obj in tags_non_affectes:
            if isinstance(tag_obj, tag):
                response_data.append(
                    {"tag": tag_obj.reference, "statut": "non_affecter"}
                )
                counts["non_affecter"] += 1

        # Traiter les items archivés
        for tag_reference in item_archive:
            response_data.append({"tag": tag_reference, "statut": "non_affecter"})
            counts["non_affecter"] += 1

        # Traiter les tags manquants (items dans l'emplacement non scannés)
        for tag_reference in tags_manquants:
            # Vérifier si c'est un message d'erreur (item sans tag)
            if isinstance(tag_reference, str) and tag_reference.startswith("Aucun tag"):
                # Item sans tag associé
                response_data.append({"tag": tag_reference, "statut": "manquant"})
                counts["manquant"] += 1
            else:
                # Récupérer l'item associé pour avoir plus d'informations
                tage = tag.objects.filter(
                    reference=tag_reference, compte=user.compte
                ).first()
                if tage:
                    item_obj_manquant = item.objects.filter(
                        tag=tage, emplacement_id=emplacement_instance.id, archive=False
                    ).first()
                    if item_obj_manquant:
                        response_data.append(
                            self.format_response(
                                item_obj_manquant, tag_reference, "manquant"
                            )
                        )
                    else:
                        response_data.append(
                            {"tag": tag_reference, "statut": "manquant"}
                        )
                else:
                    response_data.append({"tag": tag_reference, "statut": "manquant"})
                counts["manquant"] += 1

        return Response(
            {"data": response_data, "counts": counts}, status=status.HTTP_200_OK
        )

    @staticmethod
    def format_response(item_obj, tag_reference, status):
        return {
            "item_id": getattr(item_obj, "id", None),
            "item_designation": getattr(
                getattr(item_obj, "article", None), "designation", None
            ),
            "tag": tag_reference,
            "statut": status,
        }


class VerifyTagsNonPlanifierAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = request.data
        user = request.user

        # Assurez-vous que les données requises sont présentes dans la demande
        if "tags" not in data or "emplacement_id" not in data:
            return Response(
                {"error": "Les tags et l'ID de l'emplacement sont requis."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        tags = data["tags"]
        emplacement_id = data["emplacement_id"]

        # Appelez les fonctions pour vérifier les tags
        tags_inconnus = verifier_tags(tags, user)[1]
        tags_affectes, tags_non_affectes = verifier_tags_affecter(tags, user)
        tags_trouvables, tags_manquants = verifier_tags_manquants(tags, emplacement_id)
        bons_emplacements, mauvais_emplacements = verifier_emplacement_tags(
            tags, emplacement_id, user
        )
        # Initialize counters
        counts = {
            "trouvee": 0,
            "inconnu": 0,
            "manquant": 0,
            "non_affecter": 0,
            "intru": 0,
            "archive": 0,
        }

        # Prepare the response data
        response_data = []

        # Batch-fetch items for bons_emplacements and mauvais_emplacements (tag objects)
        scan_tags = bons_emplacements + mauvais_emplacements
        items_by_tag_id = {
            i.tag_id: i
            for i in item.objects.filter(tag__in=scan_tags).select_related("tag", "article")
        }

        for tage in bons_emplacements:
            item_obj = items_by_tag_id.get(tage.id)
            if item_obj is None:
                response_data.append(
                    {"item_id": None, "item_designation": None, "tag": tage.reference, "statut": "inconnu"}
                )
                counts["inconnu"] += 1
            elif item_obj.archive == True and item_obj.article:
                response_data.append(
                    {
                        "item_id": item_obj.id,
                        "item_designation": item_obj.article.designation,
                        "tag": tage.reference,
                        "statut": "archive",
                    }
                )
                counts["archive"] += 1
            elif item_obj.article and item_obj.archive == False:
                response_data.append(
                    {
                        "item_id": item_obj.id,
                        "item_designation": item_obj.article.designation,
                        "tag": tage.reference,
                        "statut": "trouvee",
                    }
                )
                counts["trouvee"] += 1
            else:
                response_data.append(
                    {
                        "item_id": item_obj.id,
                        "item_designation": item_obj.article.designation if item_obj.article else None,
                        "tag": tage.reference,
                        "statut": "intru",
                    }
                )
                counts["intru"] += 1

        for mouvais_tage in mauvais_emplacements:
            mouvais_item_obj = items_by_tag_id.get(mouvais_tage.id)
            if mouvais_item_obj:
                response_data.append(
                    {
                        "item_id": mouvais_item_obj.id,
                        "item_designation": (
                            mouvais_item_obj.article.designation
                            if mouvais_item_obj.article
                            else None
                        ),
                        "tag": mouvais_tage.reference,
                        "statut": "intru",
                    }
                )
                counts["intru"] += 1
            else:
                response_data.append(
                    {
                        "item_id": None,
                        "item_designation": None,
                        "tag": mouvais_tage.reference,
                        "statut": "non_affecter",
                    }
                )
                counts["non_affecter"] += 1

        # Batch-fetch items for tags_manquants (reference strings)
        missing_items_qs = (
            item.objects.filter(tag__reference__in=tags_manquants, archive=False)
            .select_related("tag", "article")
        )
        missing_items_by_ref = {i.tag.reference: i for i in missing_items_qs}

        for manquants_tag_reference in tags_manquants:
            manquants_item_obj = missing_items_by_ref.get(manquants_tag_reference)
            if not manquants_item_obj:
                response_data.append(
                    {"item_id": None, "item_designation": None, "tag": manquants_tag_reference, "statut": "manquant"}
                )
            else:
                response_data.append(
                    {
                        "item_id": manquants_item_obj.id,
                        "item_designation": manquants_item_obj.article.designation if manquants_item_obj.article else None,
                        "tag": manquants_tag_reference,
                        "statut": "manquant",
                    }
                )
            counts["manquant"] += 1

        for non_affecter_tag_reference in tags_non_affectes:
            response_data.append(
                {
                    "item_id": None,
                    "item_designation": None,
                    "tag": non_affecter_tag_reference.reference,
                    "statut": "non_affecter",
                }
            )
            counts["non_affecter"] += 1

        for inconnus_tag_reference in tags_inconnus:
            response_data.append(
                {
                    "item_id": None,
                    "item_designation": None,
                    "tag": inconnus_tag_reference,
                    "statut": "inconnu",
                }
            )
            counts["inconnu"] += 1

        # Add counts to the response
        return Response(
            {"data": response_data, "counts": counts}, status=status.HTTP_200_OK
        )


class ModifierStatutInventaireEmplacement(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request):
        # Récupérer l'utilisateur authentifié
        user = request.user

        # Récupérer l'inventaire_id à partir des données de la requête
        inventaire_id = request.data.get("id")

        # active_inventaire_emplacement = inventaire_emplacement.objects.filter(
        #     affceted_at=user, statut='En cours'
        # ).exists()

        # # Si un inventaire actif existe pour l'utilisateur, retourner une réponse interdite
        # if active_inventaire_emplacement:
        #     return Response({
        #         "message": "Vous n'avez pas l'autorisation de lancer un autre inventaire, car un inventaire est déjà en cours."
        #     }, status=status.HTTP_403_FORBIDDEN)

        try:
            # Tenter de récupérer l'objet inventaire_emplacement par son ID
            inventaire_obj = get_object_or_404(inventaire_emplacement, id=inventaire_id)
        except ValueError:
            # Gérer ValueError si l'ID d'inventaire n'est pas valide
            return Response(
                {"message": "ID d'inventaire invalide."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except inventaire_emplacement.DoesNotExist:
            # Gérer l'exception DoesNotExist si aucun inventaire_emplacement avec l'ID donné n'est trouvé
            return Response(
                {"message": "Inventaire non trouvé."}, status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            # Gérer d'autres exceptions imprévues
            return Response(
                {"message": f"Erreur: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # Attribuer l'utilisateur et définir le statut sur 'En cours'
        inventaire_obj.affceted_at = user
        inventaire_obj.statut = "En cours"
        inventaire_obj.save()

        # Retourner une réponse de succès
        return Response(
            {"message": "Le statut a été modifié avec succès."},
            status=status.HTTP_200_OK,
        )


class InventaireEmplacementCountAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, inventaire_id, format=None):
        try:
            inventaire_instance = inventaire.objects.get(id=inventaire_id)

            # Récupérer tous les emplacements associés à cet inventaire
            emplacements = inventaire_emplacement.objects.filter(
                inventaire=inventaire_instance
            )

            # Compter le nombre total d'emplacements
            total_emplacements = emplacements.count()

            # Compter le nombre d'emplacements avec le statut "Terminer"
            emplacements_terminer = emplacements.filter(statut="Terminer").count()
            # Retourner le résultat dans la réponse
            data = {
                "total_emplacements": total_emplacements,
                "emplacements_terminer": emplacements_terminer,
            }

            return Response(data, status=status.HTTP_200_OK)

        except inventaire.DoesNotExist:
            # Si l'inventaire n'existe pas, renvoyer une erreur 404
            return Response(
                {"error": "Inventaire not found"}, status=status.HTTP_404_NOT_FOUND
            )


class UpdateStartAtAPIView(APIView):
    def post(self, request, *args, **kwargs):
        try:
            # Gérer le cas où request.data est une liste directement
            if isinstance(request.data, list):
                ids = request.data
            else:
                # Gérer le cas où request.data est un dictionnaire
                ids = request.data.get("ids", [])
            
            if not ids:
                return Response(
                    {"error": "No IDs provided."}, status=status.HTTP_400_BAD_REQUEST
                )
            
            # Vérifier que les objets existent avant la mise à jour
            existing_objects = inventaire_emplacement.objects.filter(id__in=ids)
            existing_count = existing_objects.count()
            
            # Mettre à jour les emplacements d'inventaire
            updated_count = existing_objects.update(start_at=True)
            
            updated_objects = inventaire_emplacement.objects.filter(id__in=ids)
            
            return Response(
                {
                    "message": "Inventaire updated successfully.",
                    "updated_count": updated_count,
                    "found_count": existing_count
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CreateDetailInventaireView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        data = request.data
        inventaire_id = data.get("inventaire_id")
        emplacement_id = data.get("emplacementId")
        list_detail = data.get("listDetail", [])

        # Récupérer les instances de l'inventaire et de l'emplacement
        try:
            inventaire_instance = inventaire.objects.get(pk=inventaire_id)
            emplacement_instance = emplacement.objects.get(pk=emplacement_id)
        except inventaire.DoesNotExist:
            return Response(
                {"error": "Inventaire non trouvé"}, status=status.HTTP_404_NOT_FOUND
            )

        # Essayer de trouver l'instance inventaire_emplacement
        inventaire_emplacement_instance = inventaire_emplacement.objects.filter(
            inventaire=inventaire_instance, emplacement=emplacement_instance
        ).first()

        if not inventaire_emplacement_instance:
            return Response(
                {"error": "Inventaire emplacement non trouvé"},
                status=status.HTTP_404_NOT_FOUND,
            )

        erreurs = []

        # Boucle à travers les détails
        for detail in list_detail:
            item_id = detail.get("item_id")
            statut = detail.get("statut")
            tag_reference = detail.get("tag")

            try:
                if item_id is None and not tag_reference:
                    erreurs.append({"error": "item_id ou tag est requis pour chaque détail"})
                    continue

                # Préparer les données pour le sérialiseur
                detail_data = {
                    "inventaire_emplacement": inventaire_emplacement_instance.id,
                    "item": item_id,
                    "tag_reference": tag_reference,
                    "etat": statut,
                }

                # Valider et enregistrer le détail de l'inventaire
                serializer = CreatDetailInventaireSerializer(data=detail_data)
                if serializer.is_valid():
                    serializer.save()
                else:
                    erreurs.append(serializer.errors)

            except item.DoesNotExist:
                erreurs.append({"error": f"Item avec l'ID {item_id} non trouvé"})
            except Exception as e:
                erreurs.append({"error": str(e)})
        inventaire_emplacement_instance.statut = "Terminer"
        inventaire_emplacement_instance.save()
        inventaire_instance.lancer_inventaire(inventaire_id)

        return Response(
            {"message": "Détail inventaire créé avec succès", "errors": erreurs},
            status=status.HTTP_201_CREATED,
        )


def get_detail_inventaire_by_compte(user):
    if user.is_authenticated:
        compte = user.compte

        # Faire la jointure avec inventaire et Compte via UserWeb
        queryset = detail_inventaire.objects.filter(inventaire__user__compte=compte)

        return queryset
    else:
        return None


import logging


class DetailInventaireListAPIView(ServerSideDataTableView):
    """
    Vue pour lister les détails d'inventaire avec support DataTable et Export Excel
    """
    model = detail_inventaire
    serializer_class = DetailInventairesSerializer
    permission_classes = [IsAuthenticated]
    
    # Configuration de l'export
    export_filename = 'detail_inventaire'

    # Configuration DataTable
    search_fields = [
        'etat',
        'tag_reference',
        'id',
        'item__article__designation',
        'item__reference_auto',
        'inventaire_emplacement__emplacement__nom',
        'item__affectation_personne__nom',
        'item__affectation_personne__prenom'
    ]
    
    # Mapping des colonnes frontend -> backend
    column_field_mapping = {
        'id': 'id',
        'etat': 'etat',
        'tag': 'tag_reference',
        'start_at': 'inventaire_emplacement__start_at',
        'item_designation': 'item__article__designation',
        'emplacement': 'inventaire_emplacement__emplacement__nom',
        'reference': 'item__reference_auto',
        'created_at': 'created_at'
    }

    # Configuration de pagination
    default_page_size = 10
    max_page_size = 100

    def get_queryset(self):
        """Queryset de base filtré par inventaire_id"""
        inventaire_id = self.kwargs.get('inventaire_id')
        
        if not self.request.user.compte:
            return detail_inventaire.objects.none()
        
        try:
            inventaire_instance = inventaire.objects.get(pk=inventaire_id)
            inventaire_emplacement_instance = inventaire_emplacement.objects.filter(
                inventaire=inventaire_instance
            ).values_list("id", flat=True)
            
            return detail_inventaire.objects.filter(
                inventaire_emplacement__in=inventaire_emplacement_instance,
                inventaire_emplacement__inventaire__user__compte=self.request.user.compte
            ).select_related(
                'item',
                'item__article',
                'item__article__produit',
                'item__article__produit__categorie',
                'item__emplacement',
                'item__departement',
                'item__affectation_personne',
                'item__tag',
                'inventaire_emplacement',
                'inventaire_emplacement__emplacement'
            ).order_by('-created_at')
        except inventaire.DoesNotExist:
            return detail_inventaire.objects.none()
    
    
    def calculate_residual_value(self, item_obj):

        if not item_obj.article:
            return None

        duree_amortissement = item_obj.article.produit.duree_amourtissement
        prix_achat = item_obj.article.prix_achat

        if duree_amortissement is None or prix_achat is None:
            return None  # If either value is missing, return None

        taut = (100 / duree_amortissement) / 100

        # Calculate the annual depreciation amount (va)
        va = taut * prix_achat

        # Calculate the number of years since purchase
        current_year = datetime.now().year
        purchase_year = item_obj.article.date_achat.year
        annee = current_year - purchase_year

        # Conditions for calculating residual value
        if annee > duree_amortissement:
            # If the item has been depreciated for longer than its useful life
            valeur_residuelle = prix_achat - (va * duree_amortissement)
        else:
            # If the item is within its useful life
            valeur_residuelle = prix_achat - (va * annee)

        # Ensure the residual value is not negative
        return max(valeur_residuelle, 0)


# ── Inventaire Delete ──────────────────────────────────────────────────────

class InventaireDeleteAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, inventaire_id):
        try:
            obj = inventaire.objects.get(pk=inventaire_id)
        except inventaire.DoesNotExist:
            return Response({"error": "Inventaire not found"}, status=status.HTTP_404_NOT_FOUND)
        if obj.statut not in ('Créé', 'Annulé'):
            return Response(
                {"error": "Cannot delete an inventory that has been started or completed"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ── Mobile: expected items for an emplacement in a campaign ────────────────

class ExpectedItemsAPIView(APIView):
    """Items attendus dans un emplacement pour une campagne donnée."""
    permission_classes = [IsAuthenticated]

    def get(self, request, inventaire_id, emplacement_id):
        user = request.user
        if not user.compte:
            return Response(
                {"error": "Utilisateur sans compte associé."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        inv = inventaire.objects.filter(
            pk=inventaire_id, user__compte=user.compte
        ).select_related('departement').first()
        if not inv:
            return Response(
                {"error": "Inventaire introuvable."},
                status=status.HTTP_404_NOT_FOUND,
            )

        emp = emplacement.objects.filter(pk=emplacement_id).first()
        if not emp:
            return Response(
                {"error": "Emplacement introuvable."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not inventaire_emplacement.objects.filter(
            inventaire=inv, emplacement=emp
        ).exists():
            return Response(
                {"error": "Cet emplacement ne fait pas partie de cette campagne."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        items_qs = item.objects.filter(
            emplacement=emp,
            archive=False,
            article__compte=user.compte,
        ).select_related(
            'article', 'tag', 'emplacement', 'affectation_personne',
        )

        if inv.departement_id is not None:
            items_qs = items_qs.filter(departement_id=inv.departement_id)

        data = [
            {
                "item_id": it.id,
                "reference_auto": it.reference_auto,
                "designation": it.article.designation if it.article else None,
                "numero_serie": it.numero_serie,
                "tag_reference": it.tag.reference if it.tag else None,
                "statut": it.statut,
                "emplacement_nom": emp.nom,
                "personne_nom": (
                    f"{it.affectation_personne.nom} {it.affectation_personne.prenom}".strip()
                    if it.affectation_personne else None
                ),
            }
            for it in items_qs
        ]

        return Response(data, status=status.HTTP_200_OK)


# ── Mobile: recorded results for an emplacement after closing ──────────────

class EmplacementResultsAPIView(APIView):
    """Résultats d'inventaire enregistrés pour un emplacement donné."""
    permission_classes = [IsAuthenticated]

    def get(self, request, inventaire_id, emplacement_id):
        user = request.user
        if not user.compte:
            return Response(
                {"error": "Utilisateur sans compte associé."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        inv = inventaire.objects.filter(
            pk=inventaire_id, user__compte=user.compte
        ).first()
        if not inv:
            return Response(
                {"error": "Inventaire introuvable."},
                status=status.HTTP_404_NOT_FOUND,
            )

        emp = emplacement.objects.filter(pk=emplacement_id).first()
        if not emp:
            return Response(
                {"error": "Emplacement introuvable."},
                status=status.HTTP_404_NOT_FOUND,
            )

        inv_emp = inventaire_emplacement.objects.filter(
            inventaire=inv, emplacement=emp
        ).first()
        if not inv_emp:
            return Response(
                {"error": "Cet emplacement ne fait pas partie de cette campagne."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        details = detail_inventaire.objects.filter(
            inventaire_emplacement=inv_emp,
        ).select_related(
            'item', 'item__article', 'item__tag',
        )

        rows = [
            {
                "item_id": d.item_id,
                "reference_auto": d.item.reference_auto if d.item else None,
                "designation": d.item.article.designation if d.item and d.item.article else None,
                "etat": d.etat,
                "tag_reference": d.item.tag.reference if d.item and d.item.tag else None,
            }
            for d in details
        ]

        counts = {"trouvee": 0, "intru": 0, "manquant": 0, "inconnu": 0, "non_affecter": 0}
        for d in details:
            if d.etat in counts:
                counts[d.etat] += 1

        return Response(
            {"results": rows, "counts": counts},
            status=status.HTTP_200_OK,
        )
