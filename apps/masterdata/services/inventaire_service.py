"""Service layer for inventaire business logic."""
from __future__ import annotations

from masterdata.repositories.inventaire_repository import (
    create_inventaire_with_emplacements,
    get_emplacements_for_location,
    get_emplacements_for_zone,
    get_inventaire_by_id,
    list_inventaires_by_compte,
    replace_inventaire_emplacements,
)


def get_inventaire_detail(inventaire_id: int):
    """Fetch inventaire or raise DoesNotExist."""
    return get_inventaire_by_id(inventaire_id)


def create_location_inventaire(user, nom: str, location_instance, date_creation=None):
    """Create an inventaire for all emplacements under a location."""
    emplacements = get_emplacements_for_location(location_instance)
    return create_inventaire_with_emplacements(
        user=user,
        nom=nom,
        categorie="Location",
        emplacements=emplacements,
        date_creation=date_creation,
    )


def create_zone_inventaire(user, nom: str, zone_instance, date_creation=None):
    """Create an inventaire for all emplacements under a zone."""
    emplacements = get_emplacements_for_zone(zone_instance)
    return create_inventaire_with_emplacements(
        user=user,
        nom=nom,
        categorie="Zone",
        emplacements=emplacements,
        date_creation=date_creation,
    )


def update_inventaire_location(inventaire_id: int, nom: str, new_location):
    """Update an inventaire's name and reassign emplacements to new location."""
    inv = get_inventaire_by_id(inventaire_id)
    inv.nom = nom
    inv.save()
    new_emps = get_emplacements_for_location(new_location)
    replace_inventaire_emplacements(inv, new_emps)
    return inv
