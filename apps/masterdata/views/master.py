from django_filters import rest_framework as django_filters
from django.views import View
from masterdata.config.CustomPageNumberPagination import CustomPageNumberPagination
from masterdata.config.ArticleFiltrage import ArticleFilter
from masterdata.config.InventaireFilterage import InventaireFilter
from masterdata.config.ItemFilterage import ItemFilter
from masterdata.serializers import *
from masterdata.serializers.master import (
    PersonneWriteSerializer, CategorieWriteSerializer, ProduitWriteSerializer,
    NatureWriteSerializer, FournisseurWriteSerializer, DepartementWriteSerializer,
    MarqueWriteSerializer, TypeTagWriteSerializer, OperationWriteSerializer,
    LocationWriteSerializer, ZoneWriteSerializer, EmplacementWriteSerializer,
    TagWriteSerializer, TagEmplacementWriteSerializer,
)
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


# ── Helpers ────────────────────────────────────────────────────────────────

def _get_user_compte(request):
    """Return the compte attached to the authenticated user, or None."""
    return getattr(request.user, 'compte', None)


def _compte_required(request):
    """Return an error Response when user has no compte."""
    return Response(
        {"error": "No associated account (compte) found for this user. Please assign a compte in the admin panel."},
        status=status.HTTP_403_FORBIDDEN,
    )


# ── List View Factories ────────────────────────────────────────────────────

def _make_tenant_list_view(model_class, serializer_class, compte_lookup='compte'):
    """Factory for tenant-scoped list views."""

    class ListView(APIView):
        permission_classes = [IsAuthenticated]

        def get(self, request):
            compte = _get_user_compte(request)
            if not compte:
                return _compte_required(request)
            queryset = model_class.objects.filter(**{compte_lookup: compte})
            return Response(serializer_class(queryset, many=True).data, status=status.HTTP_200_OK)

    ListView.__name__ = f'{model_class.__name__}ListAPIView'
    return ListView


departementsListAPIView = _make_tenant_list_view(departement, DepartementSerializer)
fournisseursListAPIView = _make_tenant_list_view(fournisseur, FournisseurSerializer)
tagsListAPIView = _make_tenant_list_view(tag, TagSerializer)
tagEmplacementsListAPIView = _make_tenant_list_view(tagEmplacement, TagEmplacementSerializer)
locationsListAPIView = _make_tenant_list_view(location, LocationSerializer)
PersonnesListAPIView = _make_tenant_list_view(Personne, PersonneSerializer)
zonesListAPIView = _make_tenant_list_view(zone, ZoneSerializer, compte_lookup='location__compte')
emplacementsListAPIView = _make_tenant_list_view(emplacement, EmplacementSerializer, compte_lookup='zone__location__compte')


from django.db.models import Count


class LocationsMobileListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        locations = location.objects.filter(compte=request.user.compte)
        serializer = LocationSerializer(locations, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ZonesMobileListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, id):
        zones = zone.objects.filter(location__compte=request.user.compte, location=id)
        serializer = ZoneSerializer(zones, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class EmplacementsMobileListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, id):
        emplacements = emplacement.objects.filter(zone__location__compte=request.user.compte, zone=id)
        serializer = EmplacementSerializer(emplacements, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class produitsListAPIView(APIView):
    def get(self, request):
        produits = produit.objects.all()
        serializer = ProduitSerializer(produits, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class naturesListAPIView(APIView):
    def get(self, request):
        natures = nature.objects.all()
        serializer = NatureSerializer(natures, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class CategoriesListAPIView(APIView):
    def get(self, request):
        categories = categorie.objects.all()
        serializer = CategorieSerializer(categories, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class marquesListAPIView(APIView):
    def get(self, request):
        marques = marque.objects.all()
        serializer = MarqueSerializer(marques, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class TypeTagsListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):

        type_tags = type_tag.objects.all()
        serializer = TypeTagSerializer(type_tags, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class zonesListFilterAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, zode_id):
        user = request.user
        if user.compte:
            zones = zone.objects.filter(location__compte=user.compte, id=zode_id)
            serializer = ZoneSerializer(zones, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            return Response(
                {"error": "No associated account found"},
                status=status.HTTP_400_BAD_REQUEST,
            )


# =============================================================================
# MASTER DATA CRUD — Create / Update / Delete endpoints
# =============================================================================

# ── CRUD Factories ─────────────────────────────────────────────────────────

def _make_global_crud_views(model_class, serializer_class, label):
    """Factory for CRUD views on entities without tenant filtering."""

    class CreateView(APIView):
        permission_classes = [IsAuthenticated]

        def post(self, request):
            serializer = serializer_class(data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)

    class UpdateView(APIView):
        permission_classes = [IsAuthenticated]

        def put(self, request, pk):
            try:
                obj = model_class.objects.get(pk=pk)
            except model_class.DoesNotExist:
                return Response({"error": f"{label} not found"}, status=status.HTTP_404_NOT_FOUND)
            serializer = serializer_class(obj, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data)

    class DeleteView(APIView):
        permission_classes = [IsAuthenticated]

        def delete(self, request, pk):
            try:
                obj = model_class.objects.get(pk=pk)
            except model_class.DoesNotExist:
                return Response({"error": f"{label} not found"}, status=status.HTTP_404_NOT_FOUND)
            obj.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

    CreateView.__name__ = f'{label}CreateAPIView'
    UpdateView.__name__ = f'{label}UpdateAPIView'
    DeleteView.__name__ = f'{label}DeleteAPIView'
    return CreateView, UpdateView, DeleteView


def _make_tenant_crud_views(model_class, serializer_class, label, compte_lookup='compte'):
    """Factory for CRUD views on tenant-scoped entities."""
    save_with_compte = (compte_lookup == 'compte')

    class CreateView(APIView):
        permission_classes = [IsAuthenticated]

        def post(self, request):
            compte = _get_user_compte(request)
            if not compte:
                return _compte_required(request)
            serializer = serializer_class(data=request.data)
            serializer.is_valid(raise_exception=True)
            if save_with_compte:
                serializer.save(compte=compte)
            else:
                serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)

    class UpdateView(APIView):
        permission_classes = [IsAuthenticated]

        def put(self, request, pk):
            compte = _get_user_compte(request)
            if not compte:
                return _compte_required(request)
            try:
                obj = model_class.objects.get(pk=pk, **{compte_lookup: compte})
            except model_class.DoesNotExist:
                return Response({"error": f"{label} not found"}, status=status.HTTP_404_NOT_FOUND)
            serializer = serializer_class(obj, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data)

    class DeleteView(APIView):
        permission_classes = [IsAuthenticated]

        def delete(self, request, pk):
            compte = _get_user_compte(request)
            if not compte:
                return _compte_required(request)
            try:
                obj = model_class.objects.get(pk=pk, **{compte_lookup: compte})
            except model_class.DoesNotExist:
                return Response({"error": f"{label} not found"}, status=status.HTTP_404_NOT_FOUND)
            obj.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

    CreateView.__name__ = f'{label}CreateAPIView'
    UpdateView.__name__ = f'{label}UpdateAPIView'
    DeleteView.__name__ = f'{label}DeleteAPIView'
    return CreateView, UpdateView, DeleteView


# ── Global entities (no tenant filtering) ──────────────────────────────────

CategorieCreateAPIView, CategorieUpdateAPIView, CategorieDeleteAPIView = \
    _make_global_crud_views(categorie, CategorieWriteSerializer, "Categorie")

ProduitCreateAPIView, ProduitUpdateAPIView, ProduitDeleteAPIView = \
    _make_global_crud_views(produit, ProduitWriteSerializer, "Produit")

NatureCreateAPIView, NatureUpdateAPIView, NatureDeleteAPIView = \
    _make_global_crud_views(nature, NatureWriteSerializer, "Nature")

MarqueCreateAPIView, MarqueUpdateAPIView, MarqueDeleteAPIView = \
    _make_global_crud_views(marque, MarqueWriteSerializer, "Marque")

TypeTagCreateAPIView, TypeTagUpdateAPIView, TypeTagDeleteAPIView = \
    _make_global_crud_views(type_tag, TypeTagWriteSerializer, "Type tag")

OperationCreateAPIView, OperationUpdateAPIView, OperationDeleteAPIView = \
    _make_global_crud_views(operation, OperationWriteSerializer, "Operation")

# ── Tenant-scoped entities (direct compte FK) ─────────────────────────────

PersonneCreateAPIView, PersonneUpdateAPIView, PersonneDeleteAPIView = \
    _make_tenant_crud_views(Personne, PersonneWriteSerializer, "Personne")

FournisseurCreateAPIView, FournisseurUpdateAPIView, FournisseurDeleteAPIView = \
    _make_tenant_crud_views(fournisseur, FournisseurWriteSerializer, "Fournisseur")

DepartementCreateAPIView, DepartementUpdateAPIView, DepartementDeleteAPIView = \
    _make_tenant_crud_views(departement, DepartementWriteSerializer, "Departement")

LocationCreateAPIView, LocationUpdateAPIView, LocationDeleteAPIView = \
    _make_tenant_crud_views(location, LocationWriteSerializer, "Location")

MasterTagCreateAPIView, MasterTagUpdateAPIView, MasterTagDeleteAPIView = \
    _make_tenant_crud_views(tag, TagWriteSerializer, "Tag")

MasterTagEmplacementCreateAPIView, MasterTagEmplacementUpdateAPIView, MasterTagEmplacementDeleteAPIView = \
    _make_tenant_crud_views(tagEmplacement, TagEmplacementWriteSerializer, "TagEmplacement")


# ── Zone CRUD (custom create validation) ───────────────────────────────────

class ZoneCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        compte = _get_user_compte(request)
        if not compte:
            return _compte_required(request)
        serializer = ZoneWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        zone_obj = serializer.save()
        if zone_obj.location.compte != compte:
            zone_obj.delete()
            return Response(
                {"error": "Location does not belong to your account"},
                status=status.HTTP_403_FORBIDDEN,
            )
        return Response(serializer.data, status=status.HTTP_201_CREATED)


_, ZoneUpdateAPIView, ZoneDeleteAPIView = \
    _make_tenant_crud_views(zone, ZoneWriteSerializer, "Zone", compte_lookup='location__compte')


# ── Emplacement CRUD (custom create validation) ───────────────────────────

class EmplacementCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        compte = _get_user_compte(request)
        if not compte:
            return _compte_required(request)
        serializer = EmplacementWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        emp_obj = serializer.save()
        if emp_obj.zone.location.compte != compte:
            emp_obj.delete()
            return Response(
                {"error": "Zone does not belong to your account"},
                status=status.HTTP_403_FORBIDDEN,
            )
        return Response(serializer.data, status=status.HTTP_201_CREATED)


_, EmplacementUpdateAPIView, EmplacementDeleteAPIView = \
    _make_tenant_crud_views(emplacement, EmplacementWriteSerializer, "Emplacement", compte_lookup='zone__location__compte')