"""Repository layer for inventaire DB operations."""
from typing import Iterable, Optional

from django.db.models import QuerySet

from masterdata.models import (
    emplacement,
    inventaire,
    inventaire_emplacement,
    item,
    location,
    zone,
    departement,
)


def get_inventaire_by_id(inventaire_id: int) -> inventaire:
    """Retrieve a single inventaire. Raises inventaire.DoesNotExist."""
    return inventaire.objects.get(pk=inventaire_id)


def list_inventaires_by_compte(compte, categorie: Optional[str] = None) -> QuerySet:
    """Return inventaires belonging to *compte*, optionally filtered by *categorie*."""
    qs = inventaire.objects.filter(user__compte=compte).select_related("user")
    if categorie:
        qs = qs.filter(categorie=categorie)
    return qs.order_by("-id")


def create_inventaire_with_emplacements(
    user,
    nom: str,
    categorie: str,
    emplacements: Iterable[emplacement],
    *,
    date_creation=None,
    departement_instance=None,
) -> inventaire:
    """Create an inventaire and associate it with the given emplacements."""
    inv = inventaire.objects.create(
        nom=nom,
        user=user,
        date_creation=date_creation,
        statut="En attente",
        categorie=categorie,
        departement=departement_instance,
    )
    for emp in emplacements:
        inventaire_emplacement.objects.create(
            inventaire=inv,
            emplacement=emp,
            statut="en attente",
        )
    return inv


def replace_inventaire_emplacements(
    inv: inventaire, new_emplacements: Iterable[emplacement]
) -> None:
    """Delete existing emplacement links and create new ones."""
    inventaire_emplacement.objects.filter(inventaire=inv).delete()
    for emp in new_emplacements:
        inventaire_emplacement.objects.create(inventaire=inv, emplacement=emp)


def get_emplacements_for_location(loc: location) -> QuerySet:
    """Return all emplacements under a location (via zones)."""
    return emplacement.objects.filter(zone__location=loc)


def get_emplacements_for_zone(z: zone) -> QuerySet:
    """Return all emplacements under a zone."""
    return emplacement.objects.filter(zone=z)
