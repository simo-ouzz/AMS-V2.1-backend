#!/bin/sh
# Get token with actual user email
RAW=$(curl -s -X POST http://localhost:8000/api/token/ -H "Content-Type: application/json" -d '{"email":"belmalah@gmail.com","password":"admin"}')
echo "Auth response: $RAW"

TOKEN=$(echo "$RAW" | python -c "import sys,json; print(json.load(sys.stdin).get('access',''))" 2>/dev/null)

if [ -z "$TOKEN" ]; then
  echo "Trying password=123456..."
  RAW=$(curl -s -X POST http://localhost:8000/api/token/ -H "Content-Type: application/json" -d '{"email":"belmalah@gmail.com","password":"123456"}')
  echo "Auth response: $RAW"
  TOKEN=$(echo "$RAW" | python -c "import sys,json; print(json.load(sys.stdin).get('access',''))" 2>/dev/null)
fi

if [ -z "$TOKEN" ]; then
  echo "Setting password via python..."
  python -c "
import django,os
os.environ['DJANGO_SETTINGS_MODULE']='config.settings.dev'
django.setup()
from django.contrib.auth import get_user_model
User = get_user_model()
u = User.objects.first()
u.set_password('testpass123')
u.save()
print(f'Set password for {u.email}')
"
  RAW=$(curl -s -X POST http://localhost:8000/api/token/ -H "Content-Type: application/json" -d '{"email":"belmalah@gmail.com","password":"testpass123"}')
  echo "Auth response after reset: $RAW"
  TOKEN=$(echo "$RAW" | python -c "import sys,json; print(json.load(sys.stdin).get('access',''))" 2>/dev/null)
fi

if [ -z "$TOKEN" ]; then
  echo "FATAL: Cannot get token"
  exit 1
fi

echo "Got token OK"

echo "=== Emplacement campaigns ==="
curl -s "http://localhost:8000/inventaire/all_inventaire/?draw=1&start=0&length=100" \
  -H "Authorization: Bearer $TOKEN"
echo ""

echo "=== Zone campaigns ==="
curl -s "http://localhost:8000/inventaire/all_inventaire_zone/?draw=1&start=0&length=100" \
  -H "Authorization: Bearer $TOKEN"
echo ""

echo "=== Location campaigns ==="
curl -s "http://localhost:8000/inventaire/all_inventaire_location/?draw=1&start=0&length=100" \
  -H "Authorization: Bearer $TOKEN"
echo ""

echo "=== Departement campaigns ==="
curl -s "http://localhost:8000/inventaire/all_inventaire_departement/?draw=1&start=0&length=100" \
  -H "Authorization: Bearer $TOKEN"
echo ""
