#!/bin/bash
# Deploy NetBox to clab-host
# Run this from your Mac: ./deploy_netbox.sh

HOST="elliot@192.168.68.53"

echo "=== Deploying NetBox to clab-host ==="
echo "You will be prompted for the password (admin123) multiple times."
echo ""

# Create directories
echo "[1/4] Creating directories..."
ssh $HOST 'mkdir -p ~/netbox/env'

# Copy docker-compose.yml
echo "[2/4] Creating docker-compose.yml..."
ssh $HOST 'cat > ~/netbox/docker-compose.yml' << 'EOF'
version: '3.8'

services:
  netbox:
    image: netboxcommunity/netbox:v4.0
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_started
    env_file: env/netbox.env
    ports:
      - "8000:8080"
    volumes:
      - netbox-media:/opt/netbox/netbox/media
      - netbox-reports:/opt/netbox/netbox/reports
      - netbox-scripts:/opt/netbox/netbox/scripts
    restart: unless-stopped

  netbox-worker:
    image: netboxcommunity/netbox:v4.0
    depends_on:
      netbox:
        condition: service_started
    env_file: env/netbox.env
    command: /opt/netbox/venv/bin/python /opt/netbox/netbox/manage.py rqworker
    restart: unless-stopped

  netbox-housekeeping:
    image: netboxcommunity/netbox:v4.0
    depends_on:
      netbox:
        condition: service_started
    env_file: env/netbox.env
    command: /opt/netbox/housekeeping.sh
    restart: unless-stopped

  postgres:
    image: postgres:16-alpine
    env_file: env/postgres.env
    volumes:
      - netbox-postgres:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U netbox"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes
    volumes:
      - netbox-redis:/data
    restart: unless-stopped

volumes:
  netbox-media:
  netbox-reports:
  netbox-scripts:
  netbox-postgres:
  netbox-redis:
EOF

# Copy env files
echo "[3/4] Creating env files..."
ssh $HOST 'cat > ~/netbox/env/netbox.env' << 'EOF'
CORS_ORIGIN_ALLOW_ALL=True
DB_HOST=postgres
DB_NAME=netbox
DB_USER=netbox
DB_PASSWORD=netbox123
REDIS_HOST=redis
REDIS_PORT=6379
SECRET_KEY=r8OwDznj!!dci#P9ghmRfdu1Ysxm0AiPeDCQhKE+N_rClfWNj
SUPERUSER_NAME=admin
SUPERUSER_EMAIL=admin@euniv.local
SUPERUSER_PASSWORD=admin123
SUPERUSER_API_TOKEN=0123456789abcdef0123456789abcdef01234567
SKIP_SUPERUSER=false
EOF

ssh $HOST 'cat > ~/netbox/env/postgres.env' << 'EOF'
POSTGRES_USER=netbox
POSTGRES_PASSWORD=netbox123
POSTGRES_DB=netbox
EOF

# Start NetBox
echo "[4/4] Starting NetBox containers..."
ssh $HOST 'cd ~/netbox && docker compose up -d'

echo ""
echo "=== Deployment complete ==="
echo "NetBox will be available at: http://192.168.68.53:8000"
echo "Wait 2-3 minutes for initialization, then login with admin/admin123"
