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


class operationsListAPIView(APIView):
    def get(self, request):
        operations = operation.objects.all()
        serializer = OperationSerializer(operations, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class AddOperationItemView(APIView):
    def post(self, request):
        data = request.data
        try:
            tag_instance = tag.objects.get(reference=data["tag_reference"])
        except tag.DoesNotExist:
            return Response(
                {"error": "Tag not found"}, status=status.HTTP_404_NOT_FOUND
            )
        # Find the item related to the tag
        try:
            item_instance = item.objects.get(tag=tag_instance)
        except item.DoesNotExist:
            return Response(
                {"error": "Item not found for the given tag"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Get the operation based on the ID received in the request
        try:
            operation_instance = operation.objects.get(id=data["operation_id"])
        except operation.DoesNotExist:
            return Response(
                {"error": "Operation not found"}, status=status.HTTP_404_NOT_FOUND
            )

        # Create the new operation_article entry
        serializer = OperationItemSerializer(
            data={
                "item": item_instance.id,
                "operation": operation_instance.id,
                "prix": data.get("prix"),  # Prix de l'opération
                "date_operation": data.get("date_operation"),  # Date de l'opération
                "attachement": request.FILES.get(
                    "attachement"
                ),  # Use request.FILES for file uploads
                "commentaire": data.get("commentaire"),  # This can be a comment or null
            }
        )

        # Validate and save the operation_article instance
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"message": "operation added successfully"},
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class OperationItemListAPIView(ServerSideDataTableView):
    """
    Vue pour lister les opérations d'un item avec support DataTable
    
    Fonctionnalités automatiques :
    - Pagination côté serveur
    - Recherche globale et par colonnes
    - Tri multi-colonnes
    - Filtres avancés
    - Export Excel/CSV
    """
    model = operation_article
    serializer_class = OperationItemsSerializer
    permission_classes = [IsAuthenticated]
    
    # Configuration de l'export
    export_filename = 'operations_item'
    
    # Configuration DataTable
    search_fields = [
        'operation__reference',
        'item__article__designation',
        'item__reference_auto',
        'commentaire'
    ]
    
    # Mapping des colonnes frontend -> backend
    column_field_mapping = {
        'id': 'id',
        'operation_reference': 'operation__reference',
        'item_designation': 'item__article__designation',
        'item_reference': 'item__reference_auto',
        'commentaire': 'commentaire',
        'created_at': 'created_at'
    }

    # Configuration de pagination
    default_page_size = 10
    max_page_size = 100

    def get_queryset(self):
        """Queryset de base - opérations d'un item spécifique"""
        item_id = self.kwargs.get('item_id')
        
        if not item_id:
            return operation_article.objects.none()
        
        try:
            item_instance = item.objects.get(pk=item_id)
            
            if not self.request.user.compte:
                return operation_article.objects.none()
            
            return operation_article.objects.filter(
                item__article__compte=self.request.user.compte,
                item=item_instance
            ).select_related(
                'operation',
                'item',
                'item__article',
                'item__tag'
            ).order_by('-created_at')
            
        except item.DoesNotExist:
            return operation_article.objects.none()
    
    def get(self, request, item_id, *args, **kwargs):
        """Override pour passer item_id au queryset"""
        self.kwargs['item_id'] = item_id
        return super().get(request, *args, **kwargs)


# ── operation_article Update / Delete ──────────────────────────────────────

class OperationArticleUpdateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request, pk):
        try:
            obj = operation_article.objects.get(pk=pk)
        except operation_article.DoesNotExist:
            return Response({"error": "Operation article not found"}, status=status.HTTP_404_NOT_FOUND)
        serializer = OperationItemSerializer(obj, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class OperationArticleDeleteAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        try:
            obj = operation_article.objects.get(pk=pk)
        except operation_article.DoesNotExist:
            return Response({"error": "Operation article not found"}, status=status.HTTP_404_NOT_FOUND)
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

