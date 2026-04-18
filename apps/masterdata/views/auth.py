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


class UserDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user  # This is the user associated with the token
        user_data = {
            "id": user.id,
            "nom": user.nom,
            "prenom": user.prenom,
            "email": user.email,
            "compte_id": user.compte_id,
        }
        return Response(user_data, status=200)


class LoginUserView(APIView):
    def post(self, request):
        data = request.data
        email = data.get("email")
        password = data.get("password")

        try:
            user = UserWeb.objects.get(email=email)
            if user.check_password(password, user.password):
                return Response(
                    {"email": user.email, "username": f"{user.nom} {user.prenom}"}
                )

            else:
                return Response(
                    {"status": "failed", "msg": "invalid username or password"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        except UserWeb.DoesNotExist:
            return Response(
                {"status": "failed", "msg": "invalid username or password"},
                status=status.HTTP_400_BAD_REQUEST,
            )


from django.contrib.auth.decorators import login_required


@login_required


def assign_groups_view(request):
    users = UserWeb.objects.all()
    groups = Group.objects.all()

    if request.method == "POST":
        user_id = request.POST.get("user_id")
        group_ids = request.POST.getlist("group_ids")
        try:
            user = UserWeb.objects.get(id=user_id)
            selected_groups = Group.objects.filter(id__in=group_ids)
            user.groups.set(selected_groups)
            messages.success(
                request,
                f"Les groupes ont été mis à jour pour l'utilisateur {user.email}.",
            )
        except UserWeb.DoesNotExist:
            messages.error(request, "Utilisateur non trouvé.")
        return redirect("assign-groups")

    context = {
        "title": "Affecter les utilisateurs aux groupes",
        "users": users,
        "groups": groups,
    }
    return render(request, "admin/assign_groups.html", context)


class UserPermissionsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        # Récupérer tous les groupes auxquels l'utilisateur appartient
        groups = user.groups.all()

        # Initialiser une liste pour la réponse
        permissions_list = []

        # Parcourir chaque groupe et récupérer ses permissions
        for group in groups:
            permissions = group.permissions.all()
            group_permissions = [f"{perm.codename}" for perm in permissions]
            permissions_list.extend(group_permissions)

        # Supprimer les doublons
        permissions_list = list(set(permissions_list))

        return Response({"permissions": permissions_list})


class UserListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        if not user.compte_id:
            return Response([], status=status.HTTP_200_OK)

        users = (
            UserWeb.objects.filter(compte_id=user.compte_id)
            .order_by("nom", "prenom", "email")
            .values("id", "nom", "prenom", "email")
        )

        data = [
            {
                "id": entry["id"],
                "nom": entry["nom"] or "",
                "prenom": entry["prenom"] or "",
                "email": entry["email"] or "",
            }
            for entry in users
        ]
        return Response(data, status=status.HTTP_200_OK)


# =============================================================================
# VUES DATATABLES - Nouvelles vues avec intégration du package datatables
# =============================================================================


