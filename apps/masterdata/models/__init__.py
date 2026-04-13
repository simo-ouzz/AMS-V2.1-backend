"""Masterdata models package.

Re-exports all model classes so that existing code using
``from masterdata.models import *`` or ``from masterdata.models import article``
continues to work without changes.
"""

from .user import Compte, UserWebManager, UserWeb, SuperUserProxy  # noqa: F401
from .master import (  # noqa: F401
    Personne, categorie, produit, nature, fournisseur,
    operation, departement, marque, type_tag, Fichier,
)
from .location import location, zone, emplacement  # noqa: F401
from .asset import article, item, TransferHistorique, ArchiveItem  # noqa: F401
from .tag import tag, tagEmplacement, TagHistory, TagHistoryEmplacement  # noqa: F401
from .inventory import operation_article, inventaire, inventaire_emplacement, detail_inventaire  # noqa: F401
