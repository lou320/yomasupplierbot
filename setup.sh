#!/bin/bash
# Quick Setup Script for Yoma Supplier Bot

echo "🚀 Setting up Yoma Supplier Bot..."

# Check if .env exists
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo "⚠️  Please edit .env and add your TELEGRAM_BOT_TOKEN and DJANGO_SECRET_KEY"
    echo ""
fi

# Run migrations
echo "🔄 Running database migrations..."
python manage.py makemigrations
python manage.py migrate

# Check if superuser exists
echo ""
echo "👤 Create a superuser for Django Admin:"
python manage.py createsuperuser

# Create media directory
echo ""
echo "📁 Creating media directory..."
mkdir -p media/products

echo ""
echo "✅ Setup complete!"
echo ""
echo "To start the application, run:"
echo "  python manage.py runserver_and_bot"
echo ""
echo "Then visit http://localhost:8000/admin to manage products"
