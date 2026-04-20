"""Serializers package for the masterdata app.

Re-exports all serializer classes so that existing code using
``from masterdata.serializers import *`` continues to work.
"""

from .user import (
    UserLoginSerializer,
    UserAdminSerializer,
    UserAdminCreateSerializer,
    UserAdminUpdateSerializer,
)  # noqa: F401
from .master import (  # noqa: F401
    ProduitSerializer, MarqueSerializer, DepartementSerializer,
    TypeTagSerializer, FournisseurSerializer, NatureSerializer,
    CategorieSerializer, PersonneSerializer, LocationSerializer,
    ZoneSerializer, EmplacementSerializer, OperationSerializer, TagSerializer,
    PersonneWriteSerializer, CategorieWriteSerializer, ProduitWriteSerializer,
    NatureWriteSerializer, FournisseurWriteSerializer, DepartementWriteSerializer,
    MarqueWriteSerializer, TypeTagWriteSerializer, OperationWriteSerializer,
    LocationWriteSerializer, ZoneWriteSerializer, EmplacementWriteSerializer,
    TagEmplacementSerializer,
    TagWriteSerializer, TagEmplacementWriteSerializer,
)
from .article import (  # noqa: F401
    ArticleSerializer, EditArticleSerializer, ArticleSerializeres,
    EditItemArticleSerializer, CreateOneArticleSerializer,
    CreateArticleSerializer, UpdateItemArticleSerializer,
)
from .item import (  # noqa: F401
    EditItemSerializer, ItemsSerializer, ItemNewSerializer,
    ArchiveItemSerializer, ArchiveItemExcelImportSerializer,
    ArchiveItemBatchSerializer, ItemCountSerializer,
)
from .inventory import (  # noqa: F401
    InventaireEmplacementSerializer, InventairesEmplacementSerializer,
    InventaireSerializer, InventaireLocationSerializer,
    InventaireZoneSerializer, InventaireDepartementSerializer,
    InventaireEmplacementDetailSerializer, InventaireEmplacementSimpleSerializer,
    DetailInventaireSerializer, CreatDetailInventaireSerializer,
    DetailInventairesSerializer,
)
from .operation import OperationItemsSerializer, OperationItemSerializer  # noqa: F401
from .tag import TagHistorySerializer, TagAffectationSerializer  # noqa: F401
from .transfer import TransferHistoriqueSimpleSerializer, TransferHistoriqueSerializer  # noqa: F401
from .kpi import (  # noqa: F401
    CategorieItemCountSerializer, TypeTagCountSerializer,
    ArticleCountSerializer, tagsCountSerializer, ArchivedItemsCountSerializer,
    AmortizationCountSerializer, FinancialValueSerializer,
    LocationWithEmplacementCountSerializer, DepartementCountSerializer,
    PersonneItemSummarySerializer,
)
