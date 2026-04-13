"""Quick diagnostic script for checking API reference data."""
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.prod')

import django
django.setup()

from django.contrib.auth import get_user_model
from masterdata.models.location import location, zone, emplacement
from masterdata.models.master import departement
from masterdata.serializers.master import LocationSerializer, ZoneSerializer, EmplacementSerializer, DepartementSerializer

User = get_user_model()

print("=== DB COUNTS ===")
print(f"Locations: {location.objects.count()}")
print(f"Zones: {zone.objects.count()}")
print(f"Emplacements: {emplacement.objects.count()}")
print(f"Departements: {departement.objects.count()}")

print("\n=== USERS ===")
for u in User.objects.all()[:5]:
    print(f"  {u.email} superuser={u.is_superuser} compte_id={getattr(u, 'compte_id', None)}")

print("\n=== SAMPLE SERIALIZED DATA ===")
locs = location.objects.all()[:2]
print(f"Location sample: {LocationSerializer(locs, many=True).data}")

zones_qs = zone.objects.all()[:2]
print(f"Zone sample: {ZoneSerializer(zones_qs, many=True).data}")

emps = emplacement.objects.all()[:2]
print(f"Emplacement sample: {EmplacementSerializer(emps, many=True).data}")

deps = departement.objects.all()[:2]
print(f"Departement sample: {DepartementSerializer(deps, many=True).data}")
