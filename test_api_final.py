import django, os
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings.dev'
django.setup()

from django.contrib.auth import get_user_model
User = get_user_model()

u = User.objects.filter(email='belmalah@gmail.com').first()
if u:
    u.set_password('testpass123')
    u.save()
    print(f'Password set for {u.email}, compte={u.compte}')

import requests

r = requests.post('http://localhost:8000/api/token/', json={'email': 'belmalah@gmail.com', 'password': 'testpass123'})
print('Auth status:', r.status_code)
data = r.json()
token = data.get('access', '')
if not token:
    print('Auth failed:', data)
    exit(1)

print('Got token OK')

for scope, url in [
    ('Emplacement', '/api/inventaire/all_inventaire/'),
    ('Zone', '/api/inventaire/all_inventaire_zone/'),
    ('Location', '/api/inventaire/all_inventaire_location/'),
    ('Departement', '/api/inventaire/all_inventaire_departement/'),
]:
    print(f'\n=== {scope} campaigns ===')
    r = requests.get(f'http://localhost:8000{url}', params={'draw': 1, 'start': 0, 'length': 100},
                     headers={'Authorization': f'Bearer {token}'})
    print(f'Status: {r.status_code}')
    if r.status_code == 200:
        d = r.json()
        print(f'recordsTotal: {d.get("recordsTotal", "N/A")}')
        print(f'data count: {len(d.get("data", []))}')
        if d.get("data"):
            print(f'First item: {d["data"][0]}')
    else:
        print(f'Body: {r.text[:300]}')

# Try creating one
print('\n=== Creating test campaign (Location scope) ===')
r = requests.post('http://localhost:8000/api/inventaire/create_inventaire_location/',
                   json={'nom': 'Test API Campagne', 'location_id': 1, 'date_creation': '2025-01-15'},
                   headers={'Authorization': f'Bearer {token}'})
print(f'Create status: {r.status_code}')
print(f'Create body: {r.text[:300]}')

# Re-fetch location campaigns
print('\n=== Location campaigns after create ===')
r = requests.get('http://localhost:8000/api/inventaire/all_inventaire_location/',
                 params={'draw': 1, 'start': 0, 'length': 100},
                 headers={'Authorization': f'Bearer {token}'})
print(f'Status: {r.status_code}')
if r.status_code == 200:
    d = r.json()
    print(f'recordsTotal: {d.get("recordsTotal", "N/A")}')
    print(f'data count: {len(d.get("data", []))}')
    for item in d.get("data", []):
        print(f'  -> id={item.get("id")} ref={item.get("reference")} nom/libelle={item.get("libelle") or item.get("nom")} statut={item.get("statut")}')
