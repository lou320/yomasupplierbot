#!/bin/bash

# ==================================================================
# Yoma Supplier Bot - Production Deployment Script
# For Digital Ocean VPS (Ubuntu/Debian)
# ==================================================================

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}============================================================${NC}"
echo -e "${BLUE}   Yoma Supplier Bot - Production Deployment${NC}"
echo -e "${BLUE}============================================================${NC}\n"

# Function to print colored messages
print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

# Check if running as root (not recommended for production)
if [ "$EUID" -eq 0 ]; then 
    print_warning "Running as root. Consider using a non-root user for security."
fi

# 1. Update system packages
print_status "Updating system packages..."
sudo apt-get update -qq

# 2. Install required system packages
print_status "Installing required system packages..."
sudo apt-get install -y python3 python3-pip python3-venv python3-dev \
    build-essential libpq-dev git supervisor nginx \
    curl wget unzip > /dev/null 2>&1

# 3. Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    print_status "Creating Python virtual environment..."
    python3 -m venv venv
else
    print_status "Virtual environment already exists."
fi

# 4. Activate virtual environment
print_status "Activating virtual environment..."
source venv/bin/activate

# 5. Upgrade pip
print_status "Upgrading pip..."
pip install --upgrade pip -q

# 6. Install Python dependencies
print_status "Installing Python dependencies..."
pip install -r requirements.txt -q

# 7. Check for .env file
if [ ! -f ".env" ]; then
    print_warning ".env file not found!"
    echo -e "${YELLOW}Creating .env from .env.example...${NC}"
    cp .env.example .env
    print_error "IMPORTANT: Edit .env file with your actual credentials!"
    print_error "Run: nano .env"
    exit 1
else
    print_status ".env file found."
fi

# 8. Check for google-credentials.json
if [ ! -f "google-credentials.json" ]; then
    print_error "google-credentials.json not found!"
    print_error "Please upload your Google service account credentials file."
    exit 1
else
    print_status "Google credentials file found."
fi

# 9. Create logs directory (needed before migrations)
print_status "Creating logs directory..."
mkdir -p logs
chmod 755 logs

# 10. Run Django migrations
print_status "Running database migrations..."
python manage.py makemigrations
python manage.py migrate

# 10. Collect static files
print_status "Collecting static files..."
python manage.py collectstatic --noinput

# 11. Create superuser if needed
print_status "Checking for Django superuser..."
python manage.py shell -c "from django.contrib.auth import get_user_model; User = get_user_model(); print('Superuser exists' if User.objects.filter(is_superuser=True).exists() else exit(1))" 2>/dev/null || {
    print_warning "No superuser found. Create one now:"
    python manage.py createsuperuser
}

# 12. Test bot configuration
print_status "Testing bot configuration..."
python -c "
import os, sys, django
sys.path.insert(0, '.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from django.conf import settings
assert settings.TELEGRAM_BOT_TOKEN, 'TELEGRAM_BOT_TOKEN not set!'
assert settings.TELEGRAM_ADMIN_CHAT_ID, 'TELEGRAM_ADMIN_CHAT_ID not set!'
print('✓ Bot configuration valid')
" || {
    print_error "Bot configuration invalid! Check your .env file."
    exit 1
}

# 13. Create systemd service file
print_status "Creating systemd service..."
CURRENT_DIR=$(pwd)
USER=$(whoami)

sudo tee /etc/systemd/system/yomabot.service > /dev/null << EOF
[Unit]
Description=Yoma Supplier Telegram Bot
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$CURRENT_DIR
Environment="PATH=$CURRENT_DIR/venv/bin"
ExecStart=$CURRENT_DIR/venv/bin/python $CURRENT_DIR/manage.py runserver_and_bot --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

print_status "Systemd service created at /etc/systemd/system/yomabot.service"

# 14. Reload systemd and enable service
print_status "Enabling service..."
sudo systemctl daemon-reload
sudo systemctl enable yomabot.service


echo -e "\n${GREEN}============================================================${NC}"
echo -e "${GREEN}   Deployment Complete!${NC}"
echo -e "${GREEN}============================================================${NC}\n"

echo -e "${BLUE}Next steps:${NC}"
echo -e "1. Start the bot: ${GREEN}sudo systemctl start yomabot${NC}"
echo -e "2. Check status: ${GREEN}sudo systemctl status yomabot${NC}"
echo -e "3. View logs: ${GREEN}journalctl -u yomabot -f${NC}"
echo -e "4. Stop the bot: ${GREEN}sudo systemctl stop yomabot${NC}"
echo -e "5. Restart the bot: ${GREEN}sudo systemctl restart yomabot${NC}\n"

echo -e "${YELLOW}Optional: Configure Nginx as reverse proxy${NC}"
echo -e "Run: ${GREEN}./setup_nginx.sh${NC}\n"

print_status "Deployment script completed successfully!"
