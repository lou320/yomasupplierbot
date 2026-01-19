#!/bin/bash

# ==================================================================
# Quick Update Script - Use after git pull
# ==================================================================

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}Updating Yoma Supplier Bot...${NC}\n"

# Activate virtual environment
source venv/bin/activate

# Install/update dependencies
echo -e "${GREEN}[1/4]${NC} Installing dependencies..."
pip install -r requirements.txt -q

# Run migrations
echo -e "${GREEN}[2/4]${NC} Running migrations..."
python manage.py migrate

# Collect static files
echo -e "${GREEN}[3/4]${NC} Collecting static files..."
python manage.py collectstatic --noinput

# Restart service
echo -e "${GREEN}[4/4]${NC} Restarting bot service..."
sudo systemctl restart yomabot

echo -e "\n${GREEN}✓ Update complete!${NC}"
echo -e "Check status: ${BLUE}sudo systemctl status yomabot${NC}\n"
