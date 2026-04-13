"""
Development settings — use for local dev only.

Usage:
    export DJANGO_SETTINGS_MODULE=config.settings.dev
    python manage.py runserver
"""
from config.settings.base import *  # noqa

DEBUG = True
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_ALL_METHODS = True

# ---------------------------------------------------------------------------
# drf-spectacular — Interactive Swagger UI for visual API testing
# ---------------------------------------------------------------------------
INSTALLED_APPS += ['drf_spectacular', 'drf_spectacular_sidecar']  # noqa: F405

REST_FRAMEWORK['DEFAULT_SCHEMA_CLASS'] = 'drf_spectacular.openapi.AutoSchema'  # noqa: F405

SPECTACULAR_SETTINGS = {
    'TITLE': 'AMS-V2 — Asset Management System API',
    'DESCRIPTION': (
        'Interactive API explorer for the AMS-V2 backend.\n\n'
        '**How to authenticate:**\n'
        '1. Expand **Auth** → `POST /api/token/` → **Try it out**\n'
        '2. Enter your `email` and `password`, click **Execute**\n'
        '3. Copy the `access` value from the response\n'
        '4. Click the 🔒 **Authorize** button (top-right)\n'
        '5. Type `Bearer <paste_token_here>` → click **Authorize**\n\n'
        'All endpoints are now authenticated for testing.'
    ),
    'VERSION': '2.0.0',
    'SERVE_INCLUDE_SCHEMA': False,

    # Auto-tag endpoints by URL prefix (see config/spectacular_hooks.py)
    'PREPROCESSING_HOOKS': ['config.spectacular_hooks.custom_preprocessing_hook'],

    # Ordered tag list for the sidebar
    'TAGS': [
        {'name': 'Auth',                     'description': 'JWT login, tokens, user details, permissions'},
        {'name': 'Départements',             'description': 'Department CRUD & listing'},
        {'name': 'Personnes',                'description': 'People / staff CRUD & listing'},
        {'name': 'Locations',                'description': 'Location (building) CRUD & listing'},
        {'name': 'Zones',                    'description': 'Zone CRUD & listing'},
        {'name': 'Emplacements',             'description': 'Emplacement (room/shelf) CRUD & listing'},
        {'name': 'Catégories',               'description': 'Product category CRUD & listing'},
        {'name': 'Produits',                 'description': 'Product family CRUD & listing'},
        {'name': 'Natures',                  'description': 'Nature CRUD & listing'},
        {'name': 'Marques',                  'description': 'Brand CRUD & listing'},
        {'name': 'Fournisseurs',             'description': 'Supplier CRUD & listing'},
        {'name': 'Types de Tag',             'description': 'Tag type CRUD & listing'},
        {'name': 'Opérations',               'description': 'Operation type CRUD & listing'},
        {'name': 'Tags RFID',                'description': 'Tag create (bulk), assign, swap, delete, history'},
        {'name': 'Code-Barres',              'description': 'Code-barre items: CRUD, assign, history'},
        {'name': 'Code-Barres Emplacement',  'description': 'Code-barre emplacements: CRUD, assign, history'},
        {'name': 'QR Codes',                 'description': 'QR code items: CRUD, assign, history'},
        {'name': 'QR Codes Emplacement',     'description': 'QR code emplacements: CRUD, assign, history'},
        {'name': 'Articles',                 'description': 'Article management, import/export Excel, validation'},
        {'name': 'Items',                    'description': 'Item listing, detail, update, archive/unarchive'},
        {'name': 'Transferts',               'description': 'Bulk item transfer and transfer history'},
        {'name': 'Opérations Items',         'description': 'Maintenance/operation records on items'},
        {'name': 'Inventaires',              'description': 'Inventory creation, launch, detail, verification'},
        {'name': 'KPI / Dashboard',          'description': 'Statistics, counters, financial KPIs'},
        {'name': 'Mobile',                   'description': 'Lightweight endpoints for mobile app'},
    ],

    # JWT bearer auth scheme
    'SECURITY': [{'BearerAuth': []}],
    'APPEND_COMPONENTS': {
        'securitySchemes': {
            'BearerAuth': {
                'type': 'http',
                'scheme': 'bearer',
                'bearerFormat': 'JWT',
            }
        }
    },

    # Swagger UI customisation
    'SWAGGER_UI_SETTINGS': {
        'deepLinking': True,
        'persistAuthorization': True,
        'displayOperationId': False,
        'filter': True,
        'docExpansion': 'list',
        'defaultModelsExpandDepth': 2,
        'tagsSorter': 'alpha',
    },
    'SWAGGER_UI_DIST': 'SIDECAR',
    'SWAGGER_UI_FAVICON_HREF': 'SIDECAR',
    'REDOC_DIST': 'SIDECAR',

    # Schema generation
    'COMPONENT_SPLIT_REQUEST': True,
}
