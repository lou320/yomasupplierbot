# Yoma Supplier Bot

A production-ready Django project integrated with a Telegram Bot for managing and displaying product inventory.

## Features

- 📦 Product management with Django Admin
- 🤖 Telegram Bot integration with custom keyboards
- 🖼️ Image handling for product photos
- 📊 Stock tracking and expiry date management
- � User profile system with contact information
- 🛒 One-click ordering with automatic forwarding to admin
- 💾 Saved user info for faster future orders- 💬 **Two-way communication**: Admin can reply to orders even if users don't have Telegram usernames
- 🔗 Clickable user links in order messages for easy contact
- ⚡ Admin replies automatically forwarded to customers via bot- �🚀 Production-ready configuration

## Tech Stack

- **Backend**: Python 3.11+, Django 5.0
- **Database**: SQLite (default, easily switchable to PostgreSQL/MySQL)
- **Bot Library**: python-telegram-bot 20+ (async/await)
- **Image Processing**: Pillow

## Installation

### Local Development

1. **Clone the repository**:
   ```bash
   cd /home/violet/Documents/projects/yomasupplierbot
   ```

2. **Create a virtual environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Upgrade pip and install dependencies**:
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

4. **Set up environment variables**:
   ```bash
   cp .env.example .env
   ```
   
   Edit `.env` and add:
   - `DJANGO_SECRET_KEY`: Generate with `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`
   - `TELEGRAM_BOT_TOKEN`: Get from [@BotFather](https://t.me/botfather) on Telegram

5. **Run migrations**:
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

6. **Create a superuser**:
   ```bash
   python manage.py createsuperuser
   ```

7. **Create media directory**:
   ```bash
   mkdir -p media/products
   ```

8. **Run everything with one command**:
   ```bash
   python manage.py runserver_and_bot
   ```

## Usage

### Running Everything with One Command (Recommended)

```bash
python manage.py runserver_and_bot
```

## Production Deployment

### Deploy to Digital Ocean VPS

See [DEPLOYMENT.md](DEPLOYMENT.md) for complete production deployment guide.

**Quick Start:**

```bash
# On your VPS
git clone <your-repo-url>
cd yomasupplierbot

# Upload credentials (from your local machine)
scp .env your-vps:/path/to/yomasupplierbot/
scp google-credentials.json your-vps:/path/to/yomasupplierbot/

# Run deployment script
chmod +x deploy.sh
./deploy.sh

# Start the bot
sudo systemctl start yomabot
```

**Management:**
```bash
sudo systemctl start yomabot      # Start
sudo systemctl stop yomabot       # Stop
sudo systemctl restart yomabot    # Restart
sudo systemctl status yomabot     # Check status
journalctl -u yomabot -f          # View logs
```

**After Git Pull:**
```bash
git pull
./update.sh  # Installs deps, runs migrations, restarts service
```


This will start both the Django development server and the Telegram bot together. You can optionally specify a custom port:

```bash
python manage.py runserver_and_bot --port 8080
```

Visit `http://localhost:8000/admin` to manage products (or your custom port).

### Running Services Separately (Alternative)

If you prefer to run them separately:

**Django Admin:**
```bash
python manage.py runserver
```

**Telegram Bot:**
```bash
python manage.py runbot
```

### Bot Commands

- `/start` - Display welcome message and main menu with buttons:
  - 📦 **In Stock Products** - View available items
  - 🚚 **On The Way Products** - View incoming items

### Admin Communication System

The bot handles communication with users who don't have Telegram usernames:

**When a customer places an order:**
- Admin receives the order with a **clickable link** to the customer (works even without username)
- Customer information includes: Name, Phone, Address, Telegram first name, and User ID

**To reply to a customer:**
1. Open the order message in your admin bot chat
2. **Reply directly** to the customer info message
3. Type your message and send
4. The bot automatically forwards your message to the customer
5. You'll get a confirmation: "✅ Message sent to customer!"

**Example workflow:**
```
Customer: [Clicks order button]
Bot → Admin: "📦 NEW ORDER REQUEST
👤 Name: Ko Aung
📞 Phone: 09123456789
📍 Address: Yangon
💬 Contact Customer: [Clickable Link]
ℹ️ Reply to this message to contact the customer via bot."

Admin: [Replies to above message] "Your order is confirmed! We'll deliver tomorrow."
Bot → Customer: "📩 Message from @yomasupplier:
Your order is confirmed! We'll deliver tomorrow."
```

This system ensures you can always contact customers, regardless of their username settings!

## Project Structure

```
yomasupplierbot/
├── manage.py
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
├── config/
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
└── products/
    ├── __init__.py
    ├── models.py
    ├── admin.py
    ├── apps.py
    ├── views.py
    ├── tests.py
    └── management/
        ├── __init__.py
        └── commands/
            ├── __init__.py
            └── runbot.py
```

## Product Model Fields

- `name`: Product name
- `description`: Optional product description
- `image`: Product image (uploaded to `media/products/`)
- `price`: Decimal price
- `stock_count`: Number of units in stock
- `expiry_date`: Product expiry date
- `status`: Either "In Stock" or "On The Way"
- `created_at`: Timestamp of creation

## Deployment

For production deployment on a VPS:

1. Set `DEBUG=False` in `.env`
2. Configure `ALLOWED_HOSTS` with your domain
3. Use PostgreSQL instead of SQLite
4. Set up a proper web server (Nginx + Gunicorn)
5. Use systemd service for the bot
6. Configure SSL certificates

## License

This project is proprietary software.
