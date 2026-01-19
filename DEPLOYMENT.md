# Yoma Supplier Bot - Production Deployment Guide

## 📋 Prerequisites

- Ubuntu/Debian VPS (Digital Ocean recommended)
- Python 3.8+
- Git installed
- Domain name (optional, can use IP)
- Telegram Bot Token
- Google Service Account credentials

## 🚀 Quick Deploy to VPS

### 1. Clone Repository on VPS

```bash
# SSH into your VPS
ssh root@your-vps-ip

# Clone the repository
git clone https://github.com/yourusername/yomasupplierbot.git
cd yomasupplierbot
```

### 2. Upload Required Files

**Important:** These files are not in git (for security):

```bash
# On your local machine, upload these files:
scp .env root@your-vps-ip:/path/to/yomasupplierbot/
scp google-credentials.json root@your-vps-ip:/path/to/yomasupplierbot/
```

Or manually create/edit them on the VPS:
```bash
nano .env  # Copy from .env.example and fill in your values
nano google-credentials.json  # Paste your Google credentials
```

### 3. Run Deployment Script

```bash
# Make scripts executable
chmod +x deploy.sh update.sh setup_nginx.sh

# Run deployment (this will install everything)
./deploy.sh
```

The script will:
- ✅ Install system dependencies
- ✅ Create Python virtual environment
- ✅ Install Python packages
- ✅ Run database migrations
- ✅ Collect static files
- ✅ Create systemd service
- ✅ Set up auto-start on boot

### 4. Start the Bot

```bash
# Start the service
sudo systemctl start yomabot

# Check status
sudo systemctl status yomabot

# View live logs
journalctl -u yomabot -f
```

### 5. (Optional) Set up Nginx

```bash
# Configure Nginx as reverse proxy
./setup_nginx.sh
```

Access admin panel at: `http://your-domain.com/admin`

## 🔧 Management Commands

### Service Control
```bash
# Start
sudo systemctl start yomabot

# Stop
sudo systemctl stop yomabot

# Restart
sudo systemctl restart yomabot

# Status
sudo systemctl status yomabot

# Enable auto-start
sudo systemctl enable yomabot

# Disable auto-start
sudo systemctl disable yomabot
```

### View Logs
```bash
# Live logs
journalctl -u yomabot -f

# Last 100 lines
journalctl -u yomabot -n 100

# Logs since today
journalctl -u yomabot --since today
```

### Update After Git Pull
```bash
# Pull latest changes
git pull origin main

# Run update script
./update.sh
```

## 📁 Directory Structure (Production)

```
yomasupplierbot/
├── .env                          # Environment variables (NOT in git)
├── google-credentials.json       # Google credentials (NOT in git)
├── deploy.sh                     # Main deployment script
├── update.sh                     # Quick update script
├── setup_nginx.sh               # Nginx configuration
├── manage.py
├── requirements.txt
├── db.sqlite3                   # Database (NOT in git)
├── config/
│   ├── settings.py
│   └── ...
├── products/
│   └── management/
│       └── commands/
│           └── runserver_and_bot.py
├── media/                       # Uploaded files (NOT in git)
├── staticfiles/                 # Collected static (NOT in git)
└── venv/                        # Virtual environment (NOT in git)
```

## 🔐 Security Checklist

- [ ] Set `DEBUG=False` in `.env`
- [ ] Use strong `DJANGO_SECRET_KEY`
- [ ] Set proper `ALLOWED_HOSTS` in `.env`
- [ ] Keep `google-credentials.json` secure (chmod 600)
- [ ] Keep `.env` secure (chmod 600)
- [ ] Never commit `.env` or `google-credentials.json` to git
- [ ] Set up firewall (UFW):
  ```bash
  sudo ufw allow 22/tcp    # SSH
  sudo ufw allow 80/tcp    # HTTP
  sudo ufw allow 443/tcp   # HTTPS
  sudo ufw enable
  ```
- [ ] Set up HTTPS with Let's Encrypt:
  ```bash
  sudo apt-get install certbot python3-certbot-nginx
  sudo certbot --nginx -d yourdomain.com
  ```

## 🔄 Typical Deployment Workflow

### First Deploy
```bash
git clone <repo-url>
cd yomasupplierbot
# Upload .env and google-credentials.json
./deploy.sh
sudo systemctl start yomabot
```

### Updates
```bash
git pull
./update.sh
```

### Troubleshooting
```bash
# Check service status
sudo systemctl status yomabot

# Check logs
journalctl -u yomabot -n 50

# Test bot manually
source venv/bin/activate
python manage.py runserver_and_bot

# Restart if stuck
sudo systemctl restart yomabot
```

## 📊 Monitoring

### Check if bot is running
```bash
# Check service
systemctl is-active yomabot

# Check process
ps aux | grep runserver_and_bot
```

### Database backup
```bash
# Backup
cp db.sqlite3 db.sqlite3.backup.$(date +%Y%m%d)

# Or with cron (daily at 2 AM)
echo "0 2 * * * cd /path/to/yomasupplierbot && cp db.sqlite3 backups/db.$(date +\%Y\%m\%d).sqlite3" | crontab -
```

## 🆘 Common Issues

### Issue: Port 8000 already in use
```bash
# Find process
sudo lsof -ti:8000

# Kill process
sudo kill -9 $(sudo lsof -ti:8000)

# Restart service
sudo systemctl restart yomabot
```

### Issue: Permission denied
```bash
# Fix ownership
sudo chown -R $USER:$USER /path/to/yomasupplierbot

# Fix execute permissions
chmod +x *.sh
```

### Issue: Module not found
```bash
# Reinstall dependencies
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart yomabot
```

## 📞 Support

For issues:
1. Check logs: `journalctl -u yomabot -n 100`
2. Check service: `systemctl status yomabot`
3. Test manually: `python manage.py runserver_and_bot`

---

**Ready for production! 🚀**
