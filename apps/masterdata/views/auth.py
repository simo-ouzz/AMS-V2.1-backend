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
from django.contrib.auth.models import Permission, Group
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
            "is_staff": bool(getattr(user, "is_staff", False)),
            "is_superuser": bool(getattr(user, "is_superuser", False)),
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


def _is_admin_user(user: UserWeb) -> bool:
    return bool(getattr(user, "is_staff", False) or getattr(user, "is_superuser", False))


def _can_manage_target(request_user: UserWeb, target_user: UserWeb) -> bool:
    if getattr(request_user, "is_superuser", False):
        return True
    if not request_user.compte_id:
        return False
    return request_user.compte_id == target_user.compte_id


class AdminUserListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        if not _is_admin_user(user):
            return Response({"error": "Accès refusé."}, status=status.HTTP_403_FORBIDDEN)

        queryset = UserWeb.objects.all().select_related("compte")
        if not getattr(user, "is_superuser", False):
            queryset = queryset.filter(compte_id=user.compte_id)

        rows = queryset.order_by("nom", "prenom", "email")
        serializer = UserAdminSerializer(rows, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        user = request.user
        if not _is_admin_user(user):
            return Response({"error": "Accès refusé."}, status=status.HTTP_403_FORBIDDEN)

        payload = request.data.copy()
        if not getattr(user, "is_superuser", False):
            if not user.compte_id:
                return Response({"error": "Aucun compte assigné."}, status=status.HTTP_400_BAD_REQUEST)
            payload["compte"] = user.compte_id
            payload["is_staff"] = False

        serializer = UserAdminCreateSerializer(data=payload)
        if serializer.is_valid():
            created = serializer.save()
            return Response(UserAdminSerializer(created).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AdminUserLookupAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        if not _is_admin_user(user):
            return Response({"error": "Accès refusé."}, status=status.HTTP_403_FORBIDDEN)

        comptes_qs = Compte.objects.all().order_by("libelle")
        if not getattr(user, "is_superuser", False):
            comptes_qs = comptes_qs.filter(id=user.compte_id)

        groupes_qs = Group.objects.all().order_by("name")
        permissions_qs = Permission.objects.all().order_by("codename")

        comptes = [{"id": c.id, "label": c.libelle} for c in comptes_qs]
        groupes = [{"id": g.id, "name": g.name} for g in groupes_qs]
        permissions = [{"id": p.id, "codename": p.codename, "name": p.name} for p in permissions_qs]
        return Response(
            {
                "comptes": comptes,
                "groups": groupes,
                "permissions": permissions,
            },
            status=status.HTTP_200_OK,
        )


class AdminUserDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, user_id):
        actor = request.user
        if not _is_admin_user(actor):
            return Response({"error": "Accès refusé."}, status=status.HTTP_403_FORBIDDEN)

        try:
            target = UserWeb.objects.get(id=user_id)
        except UserWeb.DoesNotExist:
            return Response({"error": "Utilisateur non trouvé."}, status=status.HTTP_404_NOT_FOUND)

        if not _can_manage_target(actor, target):
            return Response({"error": "Accès refusé sur ce compte."}, status=status.HTTP_403_FORBIDDEN)

        payload = request.data.copy()
        if not getattr(actor, "is_superuser", False):
            payload.pop("compte", None)
            payload.pop("is_superuser", None)
            payload.pop("is_staff", None)

        serializer = UserAdminUpdateSerializer(target, data=payload, partial=True)
        if serializer.is_valid():
            updated = serializer.save()
            return Response(UserAdminSerializer(updated).data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, user_id):
        actor = request.user
        if not _is_admin_user(actor):
            return Response({"error": "Accès refusé."}, status=status.HTTP_403_FORBIDDEN)

        try:
            target = UserWeb.objects.get(id=user_id)
        except UserWeb.DoesNotExist:
            return Response({"error": "Utilisateur non trouvé."}, status=status.HTTP_404_NOT_FOUND)

        if not _can_manage_target(actor, target):
            return Response({"error": "Accès refusé sur ce compte."}, status=status.HTTP_403_FORBIDDEN)
        if target.id == actor.id:
            return Response({"error": "Action impossible sur votre propre compte."}, status=status.HTTP_400_BAD_REQUEST)

        target.is_active = False
        target.save(update_fields=["is_active"])
        return Response({"message": "Utilisateur désactivé."}, status=status.HTTP_200_OK)


# =============================================================================
# VUES DATATABLES - Nouvelles vues avec intégration du package datatables
# =============================================================================


