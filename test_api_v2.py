import requests, json

# Auth
r = requests.post('http://localhost:8000/api/token/', json={'email': 'belmalah@gmail.com', 'password': 'testpass123'})
if r.status_code != 200:
    print('Auth failed:', r.text)
    exit(1)
token = r.json()['access']
headers = {'Authorization': f'Bearer {token}'}

# Check raw response format from each list endpoint
for scope, url in [
    ('Emplacement', '/api/inventaire/all_inventaire/'),
    ('Zone', '/api/inventaire/all_inventaire_zone/'),
    ('Location', '/api/inventaire/all_inventaire_location/'),
    ('Departement', '/api/inventaire/all_inventaire_departement/'),
]:
    r = requests.get(f'http://localhost:8000{url}', params={'draw': 1, 'start': 0, 'length': 100}, headers=headers)
    print(f'\n=== {scope} (status={r.status_code}) ===')
    print(f'Keys: {list(r.json().keys()) if r.status_code == 200 else "N/A"}')
    print(f'Raw: {json.dumps(r.json(), indent=2, default=str)[:600]}')

# Get location IDs from reference data
r = requests.get('http://localhost:8000/api/locations/all_location/', headers=headers)
print(f'\nLocations: status={r.status_code}')
if r.status_code == 200:
    locs = r.json()
    for loc in locs[:5]:
        print(f'  id={loc.get("id")} nom={loc.get("nom")}')
    if locs:
        loc_id = locs[0]['id']
        print(f'\nCreating campaign with location_id={loc_id}...')
        r = requests.post('http://localhost:8000/api/inventaire/create_inventaire_location/',
                          json={'nom': 'Test Frontend Fix 2025', 'location_id': loc_id, 'date_creation': '2025-06-15'},
                          headers=headers)
        print(f'Create: status={r.status_code} body={r.text[:300]}')

        r = requests.get('http://localhost:8000/api/inventaire/all_inventaire_location/',
                         params={'draw': 1, 'start': 0, 'length': 100}, headers=headers)
        print(f'\nAfter create: status={r.status_code}')
        print(json.dumps(r.json(), indent=2, default=str)[:1500])
