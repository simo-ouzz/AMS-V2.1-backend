#!/bin/sh
# Get token
RAW=$(curl -s -X POST http://localhost:8000/api/token/ -H "Content-Type: application/json" -d '{"email":"admin@admin.com","password":"admin"}')
echo "Auth response: $RAW"

TOKEN=$(echo "$RAW" | python -c "import sys,json; print(json.load(sys.stdin).get('access',''))" 2>/dev/null)

if [ -z "$TOKEN" ]; then
  echo "Auth failed, trying different credentials..."
  RAW=$(curl -s -X POST http://localhost:8000/api/token/ -H "Content-Type: application/json" -d '{"email":"admin@admin.com","password":"Admin@123"}')
  echo "Auth response 2: $RAW"
  TOKEN=$(echo "$RAW" | python -c "import sys,json; print(json.load(sys.stdin).get('access',''))" 2>/dev/null)
fi

if [ -z "$TOKEN" ]; then
  echo "Still no token. Exiting."
  exit 1
fi

echo "Got token"

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
