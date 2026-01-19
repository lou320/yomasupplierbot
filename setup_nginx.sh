#!/bin/bash

# ==================================================================
# Nginx Configuration Script for Yoma Supplier Bot
# Optional: Sets up Nginx as reverse proxy for Django admin
# ==================================================================

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}============================================================${NC}"
echo -e "${BLUE}   Setting up Nginx for Yoma Supplier Bot${NC}"
echo -e "${BLUE}============================================================${NC}\n"

# Get domain or IP
read -p "Enter your domain name or server IP: " SERVER_NAME

if [ -z "$SERVER_NAME" ]; then
    echo -e "${YELLOW}Using localhost as default${NC}"
    SERVER_NAME="localhost"
fi

CURRENT_DIR=$(pwd)

# Create Nginx configuration
sudo tee /etc/nginx/sites-available/yomabot > /dev/null << EOF
server {
    listen 80;
    server_name $SERVER_NAME;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Admin panel
    location /admin {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    # Static files
    location /static/ {
        alias $CURRENT_DIR/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # Media files
    location /media/ {
        alias $CURRENT_DIR/media/;
        expires 7d;
    }

    # Health check
    location /health {
        access_log off;
        return 200 "healthy\n";
        add_header Content-Type text/plain;
    }
}
EOF

# Enable the site
sudo ln -sf /etc/nginx/sites-available/yomabot /etc/nginx/sites-enabled/

# Remove default site if exists
sudo rm -f /etc/nginx/sites-enabled/default

# Test Nginx configuration
echo -e "\n${BLUE}Testing Nginx configuration...${NC}"
sudo nginx -t

# Restart Nginx
echo -e "${BLUE}Restarting Nginx...${NC}"
sudo systemctl restart nginx
sudo systemctl enable nginx

echo -e "\n${GREEN}============================================================${NC}"
echo -e "${GREEN}   Nginx configured successfully!${NC}"
echo -e "${GREEN}============================================================${NC}\n"

echo -e "${BLUE}Access your admin panel at:${NC}"
echo -e "${GREEN}http://$SERVER_NAME/admin${NC}\n"

echo -e "${YELLOW}For HTTPS with Let's Encrypt (recommended):${NC}"
echo -e "sudo apt-get install certbot python3-certbot-nginx"
echo -e "sudo certbot --nginx -d $SERVER_NAME\n"
