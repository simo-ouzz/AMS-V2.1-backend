"""
drf-spectacular preprocessing hook — auto-assigns Swagger tags to every
endpoint based on its URL path prefix.  This avoids decorating each view
with @extend_schema(tags=[...]).

Used by SPECTACULAR_SETTINGS['PREPROCESSING_HOOKS'] in config/settings/dev.py.
"""

# Order matters: more-specific prefixes MUST come before less-specific ones.
# Each rule is (substring_in_path, tag_name).
_TAG_RULES = [
    # Auth
    ('token/',               'Auth'),
    ('login/',               'Auth'),
    ('detail/user/',         'Auth'),
    ('user/permissions/',    'Auth'),
    ('assign-groups/',       'Auth'),

    # Tags
    ('tag/create/',                  'Tags'),
    ('tag/affecter-tag-emplacement/','Tags'),
    ('tag/all_Tag_History/',         'Tags'),
    ('tag/delete/',                  'Tags'),
    ('tag-emplacement/',             'Tags'),
    ('tags/',                        'Tags'),
    ('assign-tag/',                  'Tags'),
    ('item/update-tag/',             'Tags'),
    ('type-tag/',                    'Types de Tag'),
    ('api/type-tag/',                'Types de Tag'),
    ('type_tags/',                   'KPI / Dashboard'),

    # Mobile
    ('mobile/', 'Mobile'),

    # Articles
    ('article/',  'Articles'),
    ('articles/', 'Articles'),

    # Items — operations on items
    ('item/add-operation-item/',    'Opérations Items'),
    ('item/update-operation-item/', 'Opérations Items'),
    ('item/delete-operation-item/', 'Opérations Items'),
    ('items/all_operation/',        'Opérations Items'),
    ('list/operation',              'Opérations Items'),

    # Items — archive, transfer, general
    ('Affectation/',                'Items'),
    ('items/annuler-affectation/',  'Items'),
    ('transfert/',                  'Transferts'),
    ('transfers/',                  'Transferts'),
    ('items/',                      'Items'),
    ('item/',                       'Items'),

    # Inventories
    ('inventaire/',              'Inventaires'),
    ('inventaire_non_planifier/','Inventaires'),

    # KPI / Dashboard
    ('kpi/',                         'KPI / Dashboard'),
    ('categories/items-count/',      'KPI / Dashboard'),
    ('locations-count/',             'KPI / Dashboard'),
    ('departements-item-count/',     'KPI / Dashboard'),
    ('valeur-residuelle',            'KPI / Dashboard'),
    ('residual-value/',              'KPI / Dashboard'),
    ('financial-value-by-department/','KPI / Dashboard'),

    # Master data CRUD & listings
    ('departements/', 'Départements'),
    ('personnes/',    'Personnes'),
    ('locations/',    'Locations'),
    ('zones/',        'Zones'),
    ('emplacements/', 'Emplacements'),
    ('categories/',   'Catégories'),
    ('produits/',     'Produits'),
    ('natures/',      'Natures'),
    ('marques/',      'Marques'),
    ('fournisseurs/', 'Fournisseurs'),
    ('operations/',   'Opérations'),

    # Config
    ('set_language/', 'Auth'),
]


def custom_preprocessing_hook(endpoints, **kwargs):
    """
    Assign a Swagger tag to each endpoint based on its URL path.
    drf-spectacular calls this before schema generation.
    """
    tagged = []
    for path, path_regex, method, callback in endpoints:
        # Try each rule in order; first match wins
        for substring, tag in _TAG_RULES:
            if substring in path:
                callback.cls.kwargs = getattr(callback.cls, 'kwargs', {})
                callback.cls.kwargs['tags'] = [tag]
                break
        tagged.append((path, path_regex, method, callback))
    return tagged
