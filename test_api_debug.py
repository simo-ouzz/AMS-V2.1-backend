import django, os, json
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings.dev'
django.setup()

from apps.masterdata.models.inventory import inventaire
from apps.masterdata.models.masterdata import location, zone, emplacement

print('DB inventory count:', inventaire.objects.count())
print('Locations:')
for loc in location.objects.all():
    print(f'  id={loc.id} nom={loc.nom}')

import requests

from django.contrib.auth import get_user_model
User = get_user_model()
u = User.objects.filter(email='belmalah@gmail.com').first()
u.set_password('testpass123')
u.save()

r = requests.post('http://localhost:8000/api/token/', json={'email': 'belmalah@gmail.com', 'password': 'testpass123'})
token = r.json()['access']

# Get raw response body
r = requests.get('http://localhost:8000/api/inventaire/all_inventaire/',
                 params={'draw': 1, 'start': 0, 'length': 100},
                 headers={'Authorization': f'Bearer {token}'})
print('\nRaw Emplacement response:')
print(json.dumps(r.json(), indent=2, default=str)[:1000])

# Create with correct location id
first_loc = location.objects.first()
if first_loc:
    print(f'\nCreating campaign with location_id={first_loc.id} ({first_loc.nom})')
    r = requests.post('http://localhost:8000/api/inventaire/create_inventaire_location/',
                       json={'nom': 'Test Frontend Fix', 'location_id': first_loc.id, 'date_creation': '2025-01-15'},
                       headers={'Authorization': f'Bearer {token}'})
    print(f'Create status: {r.status_code}')
    print(f'Create body: {r.text[:500]}')

    # Re-fetch
    r = requests.get('http://localhost:8000/api/inventaire/all_inventaire_location/',
                     params={'draw': 1, 'start': 0, 'length': 100},
                     headers={'Authorization': f'Bearer {token}'})
    print(f'\nLocation campaigns after create:')
    print(json.dumps(r.json(), indent=2, default=str)[:1500])
