#!/bin/sh
TOKEN=$(curl -s -X POST http://localhost:8000/api/token/ \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@admin.com","password":"admin"}' | python -c "import sys,json; print(json.load(sys.stdin).get('access','NO_TOKEN'))")

echo "TOKEN: $TOKEN" | head -c 40
echo "..."

echo "=== Emplacement campaigns ==="
curl -s "http://localhost:8000/inventaire/all_inventaire/?draw=1&start=0&length=100" \
  -H "Authorization: Bearer $TOKEN" | python -c "import sys,json; d=json.load(sys.stdin); print(json.dumps(d, indent=2, default=str)[:2000])"

echo ""
echo "=== Zone campaigns ==="
curl -s "http://localhost:8000/inventaire/all_inventaire_zone/?draw=1&start=0&length=100" \
  -H "Authorization: Bearer $TOKEN" | python -c "import sys,json; d=json.load(sys.stdin); print(json.dumps(d, indent=2, default=str)[:2000])"

echo ""
echo "=== Location campaigns ==="
curl -s "http://localhost:8000/inventaire/all_inventaire_location/?draw=1&start=0&length=100" \
  -H "Authorization: Bearer $TOKEN" | python -c "import sys,json; d=json.load(sys.stdin); print(json.dumps(d, indent=2, default=str)[:2000])"

echo ""
echo "=== Departement campaigns ==="
curl -s "http://localhost:8000/inventaire/all_inventaire_departement/?draw=1&start=0&length=100" \
  -H "Authorization: Bearer $TOKEN" | python -c "import sys,json; d=json.load(sys.stdin); print(json.dumps(d, indent=2, default=str)[:2000])"
