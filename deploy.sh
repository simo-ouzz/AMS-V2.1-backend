#!/bin/bash
# =============================================================================
# inventotrackV2 - VPS Deployment Script
# Run on the VPS after cloning the repo or copying files
#
# Usage:
#   chmod +x deploy.sh
#   ./deploy.sh
# =============================================================================

set -e

VPS_IP="72.62.182.196"
COMPOSE_FILE="docker-compose.prod.yml"
ENV_FILE=".env.prod"

echo "=========================================="
echo "inventotrackV2 — Production Deployment"
echo "Target: http://$VPS_IP"
echo "=========================================="

# 1. Check prerequisites
echo ""
echo "[1/6] Checking prerequisites..."
command -v docker >/dev/null 2>&1 || { echo "ERROR: docker not found. Install it first."; exit 1; }
command -v docker compose >/dev/null 2>&1 || { echo "ERROR: docker compose not found. Install docker compose plugin."; exit 1; }

# 2. Copy .env.prod → .env (docker-compose reads .env by default)
echo "[2/6] Setting up environment..."
if [ ! -f "$ENV_FILE" ]; then
    echo "ERROR: $ENV_FILE not found. Create it from .env.prod template."
    exit 1
fi
cp "$ENV_FILE" .env
echo "  .env created from $ENV_FILE"

# 3. Stop any existing containers
echo "[3/6] Stopping existing containers..."
docker compose -f "$COMPOSE_FILE" down --remove-orphans 2>/dev/null || true

# 4. Build and start — frontend-builder first to populate the volume
echo "[4/6] Building frontend..."
docker compose -f "$COMPOSE_FILE" build frontend-builder
docker compose -f "$COMPOSE_FILE" up -d frontend-builder
echo "  Waiting for frontend build to complete..."
# Wait until dist/index.html exists in the volume
for i in $(seq 1 60); do
    if docker compose -f "$COMPOSE_FILE" exec -T frontend-builder test -f /app/dist/index.html 2>/dev/null; then
        echo "  Frontend build complete!"
        break
    fi
    sleep 2
done

# 5. Build and start backend + nginx
echo "[5/6] Starting backend and nginx..."
docker compose -f "$COMPOSE_FILE" up -d --build db web nginx

# 6. Verify
echo "[6/6] Verifying deployment..."
echo "  Waiting for services to be healthy..."
sleep 10

echo ""
echo "  Container status:"
docker compose -f "$COMPOSE_FILE" ps

echo ""
echo "=========================================="
echo "Deployment complete!"
echo ""
echo "  App:   http://$VPS_IP"
echo "  API:   http://$VPS_IP/api/"
echo "  Admin: http://$VPS_IP/admin/"
echo "=========================================="
