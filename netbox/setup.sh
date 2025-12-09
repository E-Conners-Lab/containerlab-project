#!/bin/bash
# NetBox Setup Script for clab-host
# Run this on 192.168.68.53

set -e

echo "=== E-University Lab - NetBox Setup ==="
echo ""

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "Error: docker-compose not found"
    exit 1
fi

# Use 'docker compose' (v2) if available, otherwise 'docker-compose' (v1)
if docker compose version &> /dev/null; then
    COMPOSE_CMD="docker compose"
else
    COMPOSE_CMD="docker-compose"
fi

echo "Using: $COMPOSE_CMD"
echo ""

# Start containers
echo "Starting NetBox containers..."
$COMPOSE_CMD up -d

echo ""
echo "Waiting for NetBox to be ready (this may take 2-3 minutes)..."
echo ""

# Wait for NetBox to be healthy
MAX_ATTEMPTS=60
ATTEMPT=0
while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
    if curl -s http://localhost:8000/api/ > /dev/null 2>&1; then
        echo ""
        echo "NetBox is ready!"
        break
    fi
    ATTEMPT=$((ATTEMPT + 1))
    echo -n "."
    sleep 5
done

if [ $ATTEMPT -eq $MAX_ATTEMPTS ]; then
    echo ""
    echo "Warning: NetBox may not be fully ready yet. Check with: docker logs netbox-netbox-1"
fi

echo ""
echo "=== NetBox Setup Complete ==="
echo ""
echo "Access NetBox at: http://192.168.68.53:8000"
echo "Username: admin"
echo "Password: admin123"
echo "API Token: 0123456789abcdef0123456789abcdef01234567"
echo ""
echo "Next step: Run the populate script from your Mac:"
echo "  python scripts/netbox_populate.py"
echo ""
