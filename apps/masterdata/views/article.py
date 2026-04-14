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
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import transaction


class ArticlesListAPIView(ServerSideDataTableView):
    """
    API ultra-simplifiée pour les articles avec support DataTable automatique.
    
    Fonctionnalités automatiques via @datatables/:
    - Pagination côté serveur
    - Recherche globale et par colonnes
    - Tri multi-colonnes
    - Filtres avancés avec mapping automatique
    - Gestion d'erreurs
    - Support DataTable + REST API
    - Export Excel/CSV (activé par défaut)
    """
    model = article
    serializer_class = ArticleSerializer
    permission_classes = [IsAuthenticated]
    # filterset_class = ArticleFilter
    
    # Configuration de l'export
    export_filename = 'articles'
    
    # Configuration DataTable simple
    search_fields = [
        'code_article',
        'designation',
        'fournisseur__nom',
        'produit__libelle',
        'produit__categorie__libelle',
        'N_facture'
    ]
    
    # Mapping des colonnes frontend -> backend
    column_field_mapping = {
        'id': 'id',
        'code_article': 'code_article',
        'designation': 'designation',
        'categorie': 'produit__categorie__libelle',
        'date_achat': 'date_achat',
        'fournisseur': 'fournisseur__nom',
        'date_reception': 'date_reception',
        'qte': 'qte',
        'qte_recue': 'qte_recue',
        'N_facture': 'N_facture',
        'prix_achat': 'prix_achat'
    }

    # Configuration de pagination
    default_page_size = 20
    max_page_size = 100

    def get_queryset(self):
        """
        Queryset de base avec filtres métier.
        Seuls les articles valides avec quantité > 0 sont retournés.
        """
        if not self.request.user.compte:
            return article.objects.none()
            
        return article.objects.filter(
            compte=self.request.user.compte,
            qte_recue__gt=0,
            valider=True
        ).select_related(
            'produit',
            'produit__categorie',
            'fournisseur',
            'marque'
        ).prefetch_related(
            'item_set'
        )


class MobileArticleListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Récupérer tous les articles sans filtrage
        compte = request.user.compte
        queryset = article.objects.filter(compte=compte, qte_recue__gt=0, valider=True)

        # Sérialisation
        serializer = ArticleSerializeres(queryset, many=True)

        # Retourner directement les données sérialisées
        return Response(serializer.data, status=status.HTTP_200_OK)


from rest_framework.parsers import MultiPartParser, FormParser


class ArticleCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, format=None):
        data = request.data

        serializer = CreateOneArticleSerializer(data=data)

        if serializer.is_valid():
            # Affecter l'utilisateur authentifié
            article_instance = serializer.save(compte=request.user.compte)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class EditArticleAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, article_id):
        try:
            article_obj = article.objects.get(
                id=article_id
            )  # Utilise 'Article' avec une majuscule
        except article.DoesNotExist:
            return Response(
                {"message": "Article not found"}, status=status.HTTP_404_NOT_FOUND
            )

        serializer = EditArticleSerializer(
            article_obj, context={"request": request}
        )  # Passe le contexte
        return Response(serializer.data)


class ArticleUpdateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request, article_id, Format=None):
        try:
            article_obj = article.objects.get(id=article_id)
        except article.DoesNotExist:
            return Response(
                {"message": "Article not found"}, status=status.HTTP_404_NOT_FOUND
            )

        serializer = CreateOneArticleSerializer(article_obj, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ArticleDeleteAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, id_article, format=None):
        try:
            # Récupérer l'article par son ID (pk)
            article_instance = article.objects.get(pk=id_article)

            # Vérifier si qte est égale à qte_recue
            if article_instance.qte == article_instance.qte_recue:
                # Si oui, supprimer l'article
                article_instance.delete()
                return Response(
                    {"message": "Article deleted successfully"},
                    status=status.HTTP_200_OK,
                )
            else:
                # Si non, renvoyer un message d'erreur
                return Response(
                    {
                        "error": "Cannot delete article. Quantity received is not equal to the original quantity."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        except article.DoesNotExist:
            # Si l'article n'existe pas, renvoyer une erreur 404
            return Response(
                {"error": "Article not found"}, status=status.HTTP_404_NOT_FOUND
            )


class ArticleImportAPIView(APIView):
    permission_classes = [IsAuthenticated]

    REQUIRED_COLUMNS = [
        "famille",
        "N facture",
        "designation",
        "date achat",
        "prix achat",
    ]

    def post(self, request, *args, **kwargs):
        excel_file = request.FILES.get("file")
        if not excel_file:
            return Response(
                "Veuillez fournir un fichier Excel.", status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Étape 1 : Lire le fichier Excel
            df = pd.read_excel(excel_file)
        except Exception as e:
            return Response(
                f"Erreur de lecture du fichier Excel: {str(e)}",
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Étape 2 : Convertir les données en dictionnaire
        data = df.to_dict(orient="records")

        # Étape 3 : Validation des données
        errors = self.validate_data(data)

        if errors:
            errors_str = "\n".join(errors).encode("utf-8")
            return Response(errors_str, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Étape 4 : Ajouter les articles si les données sont valides
            valid_articles = self.add_articles(data, request.user)
        except Exception as e:
            return Response(
                f"Erreur lors de l'ajout des articles: {str(e)}",
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        try:
            # Étape 5 : Enregistrer les informations du fichier après succès
            fichier = self.enregistrer_fichier(excel_file, len(df))
        except Exception as e:
            return Response(
                f"Erreur lors de l'enregistrement des informations du fichier: {str(e)}",
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            {"message": "Données importées avec succès."},
            status=status.HTTP_201_CREATED,
        )

    def enregistrer_fichier(self, excel_file, nombre_lignes):
        nom_fichier = excel_file.name
        taille_fichier = excel_file.size

        fichier_existant = Fichier.objects.filter(nom=nom_fichier).first()
        if (
            fichier_existant
            and fichier_existant.taille == taille_fichier
            and fichier_existant.nombre_lignes == nombre_lignes
        ):
            raise Exception(f"Le fichier '{nom_fichier}' a déjà été importé.")

        return Fichier.objects.create(
            nom=nom_fichier, taille=taille_fichier, nombre_lignes=nombre_lignes
        )

    def validate_data(self, data):
        errors = []
        for row_index, row in enumerate(data):
            row_errors = self.validate_row(row, row_index)
            if row_errors:
                errors.extend(row_errors)
        return errors

    def validate_row(self, row, row_index):
        row_errors = []

        # Vérification des colonnes manquantes
        missing_columns = [col for col in self.REQUIRED_COLUMNS if col not in row]
        if missing_columns:
            row_errors.append(
                f"Ligne {row_index + 1}: Colonnes manquantes: {'| '.join(missing_columns)}."
            )

        # Vérification des colonnes vides
        empty_columns = [
            col for col in self.REQUIRED_COLUMNS if col in row and pd.isna(row[col])
        ]
        if empty_columns:
            row_errors.append(
                f"Ligne {row_index + 1}: Colonnes vides: {'| '.join(empty_columns)}."
            )

        # Validation des clés étrangères
        self.validate_foreign_keys(row, row_index, row_errors)

        return row_errors

    def validate_foreign_keys(self, row, row_index, row_errors):
        self.get_foreign_key_instance(
            produit, row.get("famille"), "libelle", row_index, "famille", row_errors
        )
        self.get_foreign_key_instance(
            marque, row.get("marque"), "nom", row_index, "marque", row_errors
        )
        self.get_foreign_key_instance(
            fournisseur,
            row.get("fournisseur"),
            "nom",
            row_index,
            "fournisseur",
            row_errors,
        )
        self.get_foreign_key_instance(
            nature, row.get("nature"), "libelle", row_index, "nature", row_errors
        )

    def get_foreign_key_instance(
        self, model, value, lookup_field, row_index, field_name, row_errors
    ):
        if pd.isna(value):
            return None

        try:
            return model.objects.get(
                **{lookup_field: value}
            )  # Assure une instance unique
        except model.DoesNotExist:
            row_errors.append(
                f"Ligne {row_index + 1}: {field_name} '{value}' non trouvé."
            )
        except model.MultipleObjectsReturned:
            row_errors.append(
                f"Ligne {row_index + 1}: {field_name} '{value}' correspond à plusieurs enregistrements."
            )
        return None

    def add_articles(self, data, user):
        valid_articles = []
        for row_index, row in enumerate(data):
            try:
                article_data = self.construct_article_data(row, user)

                # Créer l'instance d'article
                with transaction.atomic():
                    article_instance = article(**article_data)
                    article_instance.save()
                    valid_articles.append(article_instance)

            except Exception as e:
                raise Exception(
                    f"Ligne {row_index + 1}: Erreur inattendue lors de l'enregistrement: {str(e)}."
                )

        return valid_articles

    def construct_article_data(self, row, user):
        produit_instance = self.get_foreign_key_instance(
            produit, row.get("famille"), "libelle", 0, "famille", []
        )
        marque_instance = self.get_foreign_key_instance(
            marque, row.get("marque"), "nom", 0, "marque", []
        )
        fournisseur_instance = self.get_foreign_key_instance(
            fournisseur, row.get("fournisseur"), "nom", 0, "fournisseur", []
        )
        nature_instance = self.get_foreign_key_instance(
            nature, row.get("nature"), "libelle", 0, "nature", []
        )

        qte_value = row.get("qte")
        if pd.isna(qte_value):
            qte_value = 1

        return {
            "designation": row.get("designation"),
            "date_achat": row.get("date achat"),
            "numero_comptable": row.get("numero_comptable"),
            "couleur": row.get("couleur"),
            "poids": row.get("poids"),
            "volume": row.get("volume"),
            "langueur": row.get("langueur"),
            "hauteur": row.get("hauteur"),
            "largeur": row.get("largeur"),
            "date_expiration": self.extract_date(row.get("date expiration")),
            "date_peremption": self.extract_date(row.get("date peremption")),
            "prix_achat": row.get("prix achat"),
            "qte": qte_value,
            "qte_recue": row.get("qte_recue"),
            "N_facture": row.get("N facture"),
            "valider": True,
            "via_erp": False,
            "compte": user.compte,
            "produit": produit_instance,
            "marque": marque_instance,
            "fournisseur": fournisseur_instance,
            "nature": nature_instance,
        }

    def extract_date(self, date_value):
        if isinstance(date_value, datetime):
            return date_value.date()
        return date_value

    def collect_serializer_errors(self, serializer, errors, row_index):
        for field, field_errors in serializer.errors.items():
            value = serializer.initial_data.get(field, "Valeur non trouvée")
            error_message = f"Ligne {row_index + 1}: {field}: {'; '.join(field_errors)}; Valeur fournie: {value}"
            errors.append(error_message)


from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.permissions import IsAuthenticated


class UpdateQteRecueView(APIView):
    def put(self, request, id_article):
        try:
            article_instance = article.objects.get(pk=id_article)
        except article.DoesNotExist:
            return Response(
                {"error": "Article not found"}, status=status.HTTP_404_NOT_FOUND
            )

        if article_instance.valider:
            return Response(
                {"error": "Article is already validated and cannot be updated."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        qte_recue = request.data.get("qte_recue")
        if qte_recue is not None:
            try:
                qte_recue = int(qte_recue)
                if qte_recue > 0:
                    article_instance.qte_recue = qte_recue
                    article_instance.save()
                    return Response(
                        "la quantite a ete modifie avec succès.",
                        status=status.HTTP_200_OK,
                    )
                else:
                    return Response(
                        {"error": "qte_recue must be greater than 0"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
            except ValueError:
                return Response(
                    {"error": "qte_recue must be an integer"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            return Response(
                {"error": "qte_recue is required"}, status=status.HTTP_400_BAD_REQUEST
            )


from django.utils import timezone


class ValidateArticleView(APIView):
    def post(self, request, id_article):
        article_instance = get_object_or_404(article, pk=id_article)

        if article_instance.valider:
            return Response(
                {"error": "Article is already validated."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if article_instance.qte_recue is None or article_instance.qte is None:
            return Response(
                {"error": "Both qte and qte_recue must be set."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if article_instance.qte_recue < 0 or article_instance.qte < 0:
            return Response(
                {"error": "qte and qte_recue must be non-negative."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        current_date = timezone.now().date()
        if article_instance.qte_recue == article_instance.qte:
            article_instance.valider = True
            article_instance.save()
            return Response(
                {"message": "Article validated successfully."},
                status=status.HTTP_200_OK,
            )
        elif article_instance.qte_recue < article_instance.qte:
            with transaction.atomic():
                remaining_qte = article_instance.qte - article_instance.qte_recue
                # article_instance.qte = article_instance.qte_recue
                article_instance.valider = True
                article_instance.date_reception = current_date
                article_instance.save()

                new_article = article.objects.create(
                    code_article=article_instance.code_article,
                    designation=article_instance.designation,
                    date_achat=article_instance.date_achat,
                    numero_serie=article_instance.numero_serie,
                    numero_comptable=article_instance.numero_comptable,
                    image=article_instance.image,
                    couleur=article_instance.couleur,
                    poids=article_instance.poids,
                    volume=article_instance.volume,
                    langueur=article_instance.langueur,
                    hauteur=article_instance.hauteur,
                    largeur=article_instance.largeur,
                    date_expiration=article_instance.date_expiration,
                    date_peremption=article_instance.date_péremption,
                    date_reception=article_instance.date_reception,
                    prix_achat=article_instance.prix_achat,
                    attachement1=article_instance.attachement1,
                    attachement2=article_instance.attachement2,
                    attachement3=article_instance.attachement3,
                    qte=remaining_qte,
                    qte_recue=remaining_qte,
                    archive=article_instance.archive,
                    valider=False,
                    via_erp=article_instance.via_erp,
                    produit=article_instance.produit,
                    fournisseur=article_instance.fournisseur,
                    nature=article_instance.nature,
                )
                return Response(
                    {
                        "message": "Article validated and new article created with remaining quantity."
                    },
                    status=status.HTTP_200_OK,
                )
        else:
            return Response(
                {"error": "qte_recue cannot be greater than qte."},
                status=status.HTTP_400_BAD_REQUEST,
            )


class DuplicationView(APIView):
    def post(self, request):
        try:
            data = request.data
            article_id = data.get("article_id")
            quantity = data.get("quantity")
            emplacement_id = data.get("emplacement_id")
            departement_id = data.get("departement_id")
            numero_serie = data.get("numero_serie", "")
            personne = data.get("personne", "")
            tag_references = data.get("tag_references", [])
            if None in [article_id, quantity, emplacement_id] and 0 in [
                article_id,
                quantity,
                emplacement_id,
            ]:
                return Response(
                    {"error": "Certains champs sont manquants."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if None in [article_id, quantity, emplacement_id, departement_id] or 0 in [
                article_id,
                quantity,
                emplacement_id,
                departement_id,
            ]:
                return Response(
                    {"error": "Certains champs sont manquants."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            article_instance = get_object_or_404(article, pk=article_id)

            if article_instance.produit.statut == "en masse":
                response_data, status_code = self.process_mass_duplication(
                    article_instance,
                    quantity,
                    emplacement_id,
                    departement_id,
                    numero_serie,
                    personne,
                    tag_references,
                )
            else:
                response_data, status_code = self.process_single_duplication(
                    article_instance,
                    quantity,
                    emplacement_id,
                    departement_id,
                    numero_serie,
                    tag_references,
                    personne,
                )

            return Response(response_data, status=status_code)

        except article.DoesNotExist:
            return Response(
                {"error": "Article non trouvé."}, status=status.HTTP_404_NOT_FOUND
            )

        except ValueError as e:
            return Response(
                {"error": f"Erreur de valeur: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        except Exception as e:
            return Response(
                {"error": f"Une erreur inattendue est survenue: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @transaction.atomic
    def process_mass_duplication(
        self,
        article_instance,
        quantity,
        emplacement_id,
        departement_id,
        numero_serie,
        personne,
        tag_references,
    ):
        # Vérifiez les références des tags
        for tag_reference in tag_references:
            try:
                tag_instance = tag.objects.get(reference=tag_reference)
            except tag.DoesNotExist:
                return {
                    "error": f"Le tag avec la référence {tag_reference} est inconnu."
                }, status.HTTP_404_NOT_FOUND

            # Vérifiez si le tag est déjà affecté
            if tag_instance.affecter:
                return {
                    "error": f"Le tag avec la référence {tag_reference} est déjà affecté. La duplication n'est pas autorisée."
                }, status.HTTP_400_BAD_REQUEST

        # Vérifiez la quantité reçue
        if article_instance.qte_recue is None or article_instance.qte_recue < quantity:
            return {
                "error": "La quantité demandée dépasse la quantité reçue de l'article."
            }, status.HTTP_400_BAD_REQUEST

        # Récupération de l'instance de la personne
        personne_instance = None
        if personne != -1 and personne != 0:
            personne_instance = Personne.objects.filter(id=personne).first()

        # Récupération des instances des départements et emplacements
        departement_instance = get_object_or_404(departement, id=departement_id)
        emplacement_instance = get_object_or_404(emplacement, id=emplacement_id)

        items = []
        for tag_reference in tag_references:
            tag_instance = get_object_or_404(tag, reference=tag_reference)

            # Créez un nouvel item
            new_item = item(
                statut="affecter",
                archive=False,
                emplacement=emplacement_instance,
                departement=departement_instance,
                article=article_instance,
                tag=tag_instance,
                date_affectation=timezone.now(),
                numero_serie=numero_serie,
                affectation_personne=personne_instance,
            )
            items.append(new_item)
            tag_instance.affecter = True
            tag_instance.save()

        article_instance.qte_recue -= quantity
        article_instance.save()

        # Use individual save() to trigger AutoReferenceGeneratorMixin on each item
        for new_item in items:
            new_item.save()

        return {
            "message": "Les articles ont été dupliqués avec succès."
        }, status.HTTP_201_CREATED

    @transaction.atomic
    def process_single_duplication(
        self,
        article_instance,
        quantity,
        emplacement_id,
        departement_id,
        numero_serie,
        tag_references,
        personne,
    ):
        if article_instance.qte_recue is None or article_instance.qte_recue < quantity:
            return {
                "error": "La quantité demandée dépasse la quantité reçue de l'article."
            }, status.HTTP_400_BAD_REQUEST
        if not tag_references:
            return {
                "error": "Au moins un tag est requis pour la création."
            }, status.HTTP_400_BAD_REQUEST
        if len(tag_references) > 1:
            return {
                "error": f" Au max un tag est requis pour la création"
            }, status.HTTP_400_BAD_REQUEST
        tag_reference = tag_references[0]
        if personne != -1 and personne != 0:
            personne_instance = Personne.objects.filter(id=personne).first()
        else:
            personne_instance = None
        try:
            departement_instance = departement.objects.filter(id=departement_id).first()
        except departement.DoesNotExist:
            return {
                "error": f"departement selectionner est incunnu."
            }, status.HTTP_404_NOT_FOUND
        try:
            emplacement_instance = emplacement.objects.filter(id=emplacement_id).first()
        except emplacement.DoesNotExist:
            return {
                "error": f"emplacement selectionner est incunnu."
            }, status.HTTP_404_NOT_FOUND

        try:
            tag_instance = tag.objects.get(reference=tag_reference)
        except tag.DoesNotExist:
            return {
                f"Le tag avec la référence {tag_reference} est incunnu."
            }, status.HTTP_404_NOT_FOUND

        if tag_instance.affecter:
            return {
                "error": f"Le tag avec la référence {tag_reference} est déjà affecté. La duplication n'est pas autorisée."
            }, status.HTTP_400_BAD_REQUEST
        new_item = item(
            statut="affecter",
            archive=False,
            emplacement=emplacement_instance,
            article=article_instance,
            departement=departement_instance,
            tag=tag_instance,
            date_affectation=timezone.now(),
            numero_serie=numero_serie,
            affectation_personne=personne_instance,
        )
        new_item.save()

        tag_instance.affecter = True
        tag_instance.save()
        article_instance.qte_recue -= quantity
        article_instance.save()
        return {"message": "L'article a été crée avec succès."}, status.HTTP_201_CREATED


class ArticlesConsommesListAPIView(ServerSideDataTableView):
    """
    Vue pour lister les articles consommés (qte_recue=0) avec support DataTable
    
    Fonctionnalités automatiques via @datatables/:
    - Pagination côté serveur
    - Recherche globale et par colonnes
    - Tri multi-colonnes
    - Filtres avancés avec mapping automatique
    - Gestion d'erreurs
    - Support DataTable + REST API + Export Excel
    """
    model = article
    serializer_class = ArticleSerializer
    permission_classes = [IsAuthenticated]
    
    # Configuration de l'export
    export_filename = 'articles_consommes'
    
    
    # Configuration DataTable
    search_fields = [
        'id',
        'code_article',
        'designation',
        'numero_comptable',
        'N_facture',
        'produit__libelle',
        'fournisseur__nom',
        'produit__categorie__libelle'
    ]
    
    # Mapping des colonnes frontend -> backend
    column_field_mapping = {
        'id': 'id',
        'designation': 'designation',
        'code_article': 'code_article',
        'date_achat': 'date_achat',
        'date_reception': 'date_reception',
        'qte': 'qte',
        'qte_recue': 'qte_recue',
        'N_facture': 'N_facture',
        'prix_achat': 'prix_achat'
    }

    # Configuration de pagination
    default_page_size = 20
    max_page_size = 100

    def get_queryset(self):
        """
        Queryset de base avec filtres métier.
        Seuls les articles consommés (qte_recue=0) sont retournés.
        """
        if not self.request.user.compte:
            return article.objects.none()
            
        return article.objects.filter(
            compte=self.request.user.compte,
            qte_recue=0
        ).select_related(
            'produit',
            'produit__categorie',
            'fournisseur',
            'marque',
            'nature'
        ).order_by("-id")


class ArticleExportExcelAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Return all articles; vous pouvez modifier cette partie si nécessaire
        authenticated_user = self.request.user
        return article.objects.filter(qte_recue__gt=0).order_by("id")

    def filter_queryset(self, qs):
        search = self.request.GET.get("search[value]", None)
        ordering = self.request.GET.get("ordering", "id")
        if search:
            qs = qs.filter(
                Q(code_article__istartswith=search) | Q(designation__icontains=search)
            )
        qs = qs.order_by(ordering)
        return qs

    def get(self, request, *args, **kwargs):
        # Récupérer et filtrer les articles
        qs = self.get_queryset()
        filtered_qs = self.filter_queryset(qs)

        # Préparer les données pour l'exportation Excel
        data = filtered_qs.values(
            "code_article",
            "designation",
            "date_achat",
            "numero_comptable",
            "couleur",
            "poids",
            "volume",
            "langueur",
            "hauteur",
            "largeur",
            "prix_achat",
            "qte_recue",
        )

        # Utiliser pandas pour créer le DataFrame et exporter vers Excel
        df = pd.DataFrame(list(data))

        # Créer la réponse HTTP avec le fichier Excel
        response = HttpResponse(
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response["Content-Disposition"] = "attachment; filename=articles_filtered.xlsx"

        # Exporter les données dans le fichier Excel
        df.to_excel(response, index=False)

        return response


