# API Mobile Endpoints

Base URL: `/api/`

All authenticated endpoints require a JWT Bearer token in the `Authorization` header:
```
Authorization: Bearer <access_token>
```

---

## 1. Authentification

### POST `/login/mobile/`

Login utilisateur mobile. Aucune authentification requise.

**Request body:**
```json
{
  "email": "user@example.com",
  "password": "secret"
}
```

**Response 200:**
```json
{
  "email": "user@example.com",
  "username": "NOM Prenom"
}
```

**Response 400:**
```json
{ "status": "failed", "msg": "invalid username or password" }
```

---

## 2. Données de référence (Master data)

### GET `/mobile/all_location/`

Liste des locations du compte de l'utilisateur.

- **Auth:** JWT requis
- **Scope:** `request.user.compte`
- **Response 200:** `[{ id, nom, ... }]`

---

### GET `/mobile/zones/{id}/`

Liste des zones d'une location.

| Paramètre | Type | Description |
|-----------|------|-------------|
| `id` | int (path) | ID de la location |

- **Auth:** JWT requis
- **Scope:** `request.user.compte`
- **Response 200:** `[{ id, nom, location, ... }]`

---

### GET `/mobile/emplacements/{id}/`

Liste des emplacements d'une zone.

| Paramètre | Type | Description |
|-----------|------|-------------|
| `id` | int (path) | ID de la zone |

- **Auth:** JWT requis
- **Scope:** `request.user.compte` (via `zone__location__compte`)
- **Response 200:** `[{ id, designation, zone, ... }]`

---

### GET `/mobile/article/all_articles/`

Liste des articles validés avec stock positif.

- **Auth:** JWT requis
- **Scope:** `request.user.compte`, filtre `qte_recue > 0` et `valider = True`
- **Response 200:** `[{ id, code_article, designation, ... }]`

---

### GET `/mobile/items/count/emplacement/{emplacement_id}/`

Nombre total d'items dans un emplacement.

| Paramètre | Type | Description |
|-----------|------|-------------|
| `emplacement_id` | int (path) | ID de l'emplacement |

- **Auth:** JWT requis
- **Response 200:**
```json
{ "item_count": 33 }
```

---

## 3. Campagnes d'inventaire

### GET `/mobile/inventaire/all_inventaire/`

Liste des inventaires assignés à l'utilisateur (emplacements démarrés, non terminés).

- **Auth:** JWT requis
- **Scope:** `request.user.compte`
- **Filtres auto:** `start_at = True`, `statut != "Terminer"`

**Response 200:**
```json
[
  {
    "id": 1,
    "inventaireId": 5,
    "categorie": "Emplacement",
    "affceted_at": 3,
    "emplacementId": 121,
    "operateur": "BELMELAH Mohamed",
    "nom": "Inventaire Q1",
    "reference": "INV-000005",
    "emplacement_nom": "01/PETITE SALLE REUNION-06",
    "user": "Admin Admin",
    "created_at": "2026-01-15T10:00:00Z",
    "statut": "En cours"
  }
]
```

---

### GET `/inventaire/info/{inventaire_id}/`

Informations de base d'une campagne d'inventaire.

| Paramètre | Type | Description |
|-----------|------|-------------|
| `inventaire_id` | int (path) | ID de la campagne |

- **Auth:** JWT requis
- **Scope:** `request.user.compte`

**Response 200:**
```json
{
  "id": 5,
  "nom": "Inventaire Q1",
  "reference": "INV-000005",
  "date_creation": "2026-01-15",
  "statut": "En cours"
}
```

---

### GET `/inventaire/emplacements-count/{inventaire_id}/`

Compteurs d'avancement d'une campagne.

| Paramètre | Type | Description |
|-----------|------|-------------|
| `inventaire_id` | int (path) | ID de la campagne |

- **Auth:** JWT requis

**Response 200:**
```json
{
  "total_emplacements": 12,
  "emplacements_terminer": 4
}
```

---

## 4. Préparation du scan

### GET `/mobile/inventaire/{inventaire_id}/emplacement/{emplacement_id}/items/`

Liste des items attendus dans un emplacement **avant** le scan. Permet à l'opérateur de voir ce qui devrait être trouvé.

| Paramètre | Type | Description |
|-----------|------|-------------|
| `inventaire_id` | int (path) | ID de la campagne |
| `emplacement_id` | int (path) | ID de l'emplacement |

- **Auth:** JWT requis
- **Scope:** `request.user.compte`
- **Validations:**
  - L'inventaire doit exister et appartenir au compte
  - L'emplacement doit exister
  - L'emplacement doit faire partie de la campagne (`inventaire_emplacement` linkage)
  - Si campagne département : filtre par `departement_id`
  - Items non archivés uniquement (`archive = False`)

**Response 200:**
```json
[
  {
    "item_id": 276,
    "reference_auto": "ITEM-000276",
    "designation": "CAISSON MOBILE AVEC GALETTE",
    "numero_serie": "",
    "tag_reference": "E280691500004021A6A85CA1",
    "statut": "affecter",
    "emplacement_nom": "01/PETITE SALLE REUNION-06",
    "personne_nom": "BELMELAH Mohamed"
  }
]
```

**Response 400:**
```json
{ "error": "Cet emplacement ne fait pas partie de cette campagne." }
```

**Response 404:**
```json
{ "error": "Inventaire introuvable." }
```
```json
{ "error": "Emplacement introuvable." }
```

---

## 5. Exécution du scan

### PUT `/inventaire/lancer_inventaire/`

Démarrer le scan d'un emplacement (change le statut à "En cours" et assigne l'opérateur).

- **Auth:** JWT requis

**Request body:**
```json
{ "id": 1 }
```
> `id` = ID de l'`inventaire_emplacement`

**Response 200:**
```json
{ "message": "Le statut a été modifié avec succès." }
```

---

### POST `/inventaire/update-start-at/`

Activer le flag `start_at` pour un ensemble d'emplacements d'inventaire.

**Request body:**
```json
[1, 2, 3]
```
> Liste des IDs `inventaire_emplacement`

**Response 200:**
```json
{
  "message": "Inventaire updated successfully.",
  "updated_count": 3,
  "found_count": 3
}
```

---

### POST `/inventaire/` — Scan planifié

Envoie les tags RFID scannés pour un emplacement dans le cadre d'une campagne planifiée. Compare les tags aux items attendus et retourne le résultat du scan.

- **Auth:** JWT requis
- **Scope:** `request.user.compte`
- **Validations:**
  - `tags`, `emplacement_id`, `inventaire_id` obligatoires
  - L'emplacement doit exister
  - L'inventaire doit exister
  - **L'emplacement doit faire partie de la campagne** (guard ajouté)
  - Filtrage par département si la campagne a un `departement`

**Request body:**
```json
{
  "tags": [
    "E280691500004021A6A85CA1",
    "E280691500005021A6A85CB4",
    "TAG_INCONNU_123"
  ],
  "emplacement_id": 121,
  "inventaire_id": 5
}
```

**Response 200:**
```json
{
  "data": [
    {
      "item_id": 276,
      "item_designation": "CAISSON MOBILE AVEC GALETTE",
      "tag": "E280691500004021A6A85CA1",
      "statut": "trouvee"
    },
    {
      "item_id": null,
      "item_designation": null,
      "tag": "TAG_INCONNU_123",
      "statut": "inconnu"
    },
    {
      "item_id": 91,
      "item_designation": "PC PORTABLE DELL",
      "tag": null,
      "statut": "manquant"
    }
  ],
  "counts": {
    "trouvee": 1,
    "inconnu": 1,
    "manquant": 1,
    "non_affecter": 0,
    "intru": 0
  }
}
```

**Statuts possibles dans `data[].statut` :**

| Statut | Signification |
|--------|---------------|
| `trouvee` | Tag scanné, item au bon emplacement |
| `intru` | Tag scanné, item appartient à un autre emplacement |
| `manquant` | Item attendu dans l'emplacement mais tag non scanné |
| `inconnu` | Tag scanné non reconnu dans le système |
| `non_affecter` | Tag scanné, item existe mais n'est affecté à aucun emplacement |

**Response 400:**
```json
{ "error": "Cet emplacement ne fait pas partie de cette campagne." }
```

---

### POST `/inventaire_non_planifier/` — Scan non planifié

Même principe que le scan planifié mais sans campagne associée. Pas de validation de linkage campagne–emplacement. Inclut un statut supplémentaire `archive`.

- **Auth:** JWT requis
- **Scope:** `request.user.compte`

**Request body:**
```json
{
  "tags": ["E280691500004021A6A85CA1"],
  "emplacement_id": 121
}
```

**Response 200:**
```json
{
  "data": [
    {
      "item_id": 276,
      "item_designation": "CAISSON MOBILE",
      "tag": "E280691500004021A6A85CA1",
      "statut": "trouvee"
    }
  ],
  "counts": {
    "trouvee": 1,
    "inconnu": 0,
    "manquant": 0,
    "non_affecter": 0,
    "intru": 0,
    "archive": 0
  }
}
```

> Statut supplémentaire : `archive` — item archivé trouvé par le scan.

---

## 6. Clôture et résultats

### POST `/inventaire/create-detail-inventaire/`

Enregistre les résultats du scan et clôture l'emplacement. Crée les lignes `detail_inventaire` et passe le statut de l'emplacement à "Terminer".

- **Auth:** JWT requis
- **Transaction:** Atomique

**Request body:**
```json
{
  "inventaire_id": 5,
  "emplacementId": 121,
  "listDetail": [
    { "item_id": 276, "statut": "trouvee" },
    { "item_id": 91, "statut": "manquant" },
    { "item_id": 500, "statut": "intru" }
  ]
}
```

**Response 201:**
```json
{
  "message": "Détail inventaire créé avec succès",
  "errors": []
}
```

---

### GET `/mobile/inventaire/{inventaire_id}/emplacement/{emplacement_id}/results/`

Résultats enregistrés pour un emplacement après clôture. Permet de consulter le détail et les compteurs.

| Paramètre | Type | Description |
|-----------|------|-------------|
| `inventaire_id` | int (path) | ID de la campagne |
| `emplacement_id` | int (path) | ID de l'emplacement |

- **Auth:** JWT requis
- **Scope:** `request.user.compte`
- **Validations:** Mêmes que `/items/` (inventaire, emplacement, linkage)

**Response 200:**
```json
{
  "results": [
    {
      "item_id": 276,
      "reference_auto": "ITEM-000276",
      "designation": "CAISSON MOBILE AVEC GALETTE",
      "etat": "trouvee",
      "tag_reference": "E280691500004021A6A85CA1"
    },
    {
      "item_id": 91,
      "reference_auto": "ITEM-000091",
      "designation": "PC PORTABLE DELL",
      "etat": "manquant",
      "tag_reference": "E280691500005021A6A85CB4"
    }
  ],
  "counts": {
    "trouvee": 1,
    "intru": 0,
    "manquant": 1,
    "inconnu": 0,
    "non_affecter": 0
  }
}
```

---

## 7. Flux mobile complet

```
1. Login                         POST /login/mobile/
2. Charger les campagnes         GET  /mobile/inventaire/all_inventaire/
3. Sélectionner un emplacement
4. Voir les items attendus       GET  /mobile/inventaire/{inv}/emplacement/{emp}/items/
5. Lancer le scan                PUT  /inventaire/lancer_inventaire/
6. Scanner les tags RFID         POST /inventaire/
7. Enregistrer les résultats     POST /inventaire/create-detail-inventaire/
8. Consulter les résultats       GET  /mobile/inventaire/{inv}/emplacement/{emp}/results/
```
