# Production Deployment Checklist

## 📋 Pre-Deployment Checklist

### Local Machine (Before pushing to git)

- [ ] **Environment Variables**
  - [ ] Copy `.env.example` to `.env`
  - [ ] Set `DEBUG=False` for production
  - [ ] Generate strong `DJANGO_SECRET_KEY`
  - [ ] Set `ALLOWED_HOSTS` with your domain/IP
  - [ ] Set `TELEGRAM_BOT_TOKEN`
  - [ ] Set `TELEGRAM_ADMIN_CHAT_ID`
  - [ ] Verify all environment variables

- [ ] **Google Credentials**
  - [ ] `google-credentials.json` file exists
  - [ ] File permissions are secure (chmod 600)
  - [ ] Service account has access to Google Sheet

- [ ] **Code Review**
  - [ ] Remove debug print statements
  - [ ] Remove test scripts (or add to .gitignore)
  - [ ] Check for hardcoded secrets
  - [ ] Verify .gitignore includes sensitive files

- [ ] **Git Repository**
  - [ ] Run `./git_setup.sh` to initialize
  - [ ] Review files to be committed
  - [ ] Commit: `git commit -m "Initial commit"`
  - [ ] Create remote repository (GitHub/GitLab/Bitbucket)
  - [ ] Add remote: `git remote add origin <url>`
  - [ ] Push: `git push -u origin main`

### VPS Setup (Digital Ocean)

- [ ] **Server Preparation**
  - [ ] Create VPS droplet (Ubuntu 22.04 LTS recommended)
  - [ ] Note IP address
  - [ ] SSH access configured
  - [ ] (Optional) Domain name pointed to VPS IP

- [ ] **Initial Server Security**
  ```bash
  # Update system
  sudo apt-get update && sudo apt-get upgrade -y
  
  # Create non-root user (recommended)
  sudo adduser botuser
  sudo usermod -aG sudo botuser
  su - botuser
  
  # Set up SSH key authentication
  mkdir -p ~/.ssh
  chmod 700 ~/.ssh
  # Add your public key to ~/.ssh/authorized_keys
  
  # Set up firewall
  sudo ufw allow 22/tcp   # SSH
  sudo ufw allow 80/tcp   # HTTP
  sudo ufw allow 443/tcp  # HTTPS
  sudo ufw enable
  ```

## 🚀 Deployment Steps

### Step 1: Clone Repository

```bash
cd ~
git clone <your-repo-url> yomasupplierbot
cd yomasupplierbot
```

### Step 2: Upload Sensitive Files

**From your local machine:**
```bash
scp .env botuser@your-vps-ip:~/yomasupplierbot/
scp google-credentials.json botuser@your-vps-ip:~/yomasupplierbot/
```

**Or create directly on VPS:**
```bash
nano .env
# Paste your production environment variables

nano google-credentials.json
# Paste your Google service account JSON
```

**Secure the files:**
```bash
chmod 600 .env google-credentials.json
```

### Step 3: Run Deployment Script

```bash
chmod +x deploy.sh
./deploy.sh
```

This script will:
- Install system dependencies
- Create Python virtual environment
- Install Python packages
- Run database migrations
- Collect static files
- Create systemd service
- Enable auto-start

### Step 4: Start the Service

```bash
sudo systemctl start yomabot
sudo systemctl status yomabot
```

### Step 5: (Optional) Configure Nginx

```bash
./setup_nginx.sh
```

### Step 6: (Optional) Set up HTTPS

```bash
sudo apt-get install certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com
```

## ✅ Post-Deployment Verification

- [ ] **Service Status**
  ```bash
  sudo systemctl status yomabot
  # Should show "active (running)"
  ```

- [ ] **Check Logs**
  ```bash
  journalctl -u yomabot -n 50
  # Should show bot starting successfully
  ```

- [ ] **Test Telegram Bot**
  - [ ] Send `/start` command to bot
  - [ ] Click "In Stock" button
  - [ ] Verify products load
  - [ ] Click order button
  - [ ] Verify order reaches admin

- [ ] **Test Admin Panel**
  - [ ] Access http://your-domain.com/admin
  - [ ] Login with superuser credentials
  - [ ] Check UserProfile entries
  - [ ] Verify product models

- [ ] **Test Google Sheets Integration**
  - [ ] Update a product in Google Sheets
  - [ ] Restart bot if needed: `sudo systemctl restart yomabot`
  - [ ] Verify changes reflect in bot

## 🔄 Regular Maintenance

### Daily Checks
```bash
# Check service status
sudo systemctl status yomabot

# Check recent logs
journalctl -u yomabot --since today
```

### Weekly Backups
```bash
# Backup database
cp db.sqlite3 backups/db.$(date +%Y%m%d).sqlite3

# Or set up automated backup with cron
crontab -e
# Add: 0 2 * * * cd /home/botuser/yomasupplierbot && cp db.sqlite3 backups/db.$(date +\%Y\%m\%d).sqlite3
```

### Update Workflow
```bash
# Pull latest changes
git pull origin main

# Run update script
./update.sh

# Verify everything works
sudo systemctl status yomabot
```

## 🆘 Troubleshooting

### Bot Not Starting
```bash
# Check service status
sudo systemctl status yomabot

# Check detailed logs
journalctl -u yomabot -n 100 --no-pager

# Try running manually
source venv/bin/activate
python manage.py runserver_and_bot
```

### Port Already in Use
```bash
# Find and kill process
sudo lsof -ti:8000 | xargs sudo kill -9

# Restart service
sudo systemctl restart yomabot
```

### Google Sheets Error
```bash
# Verify credentials file exists
ls -la google-credentials.json

# Check if service account has access to sheet
# Run test script
source venv/bin/activate
python test_sheets.py
```

### Database Issues
```bash
# Backup current database
cp db.sqlite3 db.sqlite3.backup

# Run migrations
source venv/bin/activate
python manage.py migrate

# Restart service
sudo systemctl restart yomabot
```

## 📊 Monitoring Commands

```bash
# View live logs
journalctl -u yomabot -f

# Check service auto-start status
systemctl is-enabled yomabot

# Check if bot process is running
ps aux | grep runserver_and_bot

# Check memory usage
free -h

# Check disk space
df -h

# Check system load
uptime
```

## 🔒 Security Best Practices

- [ ] Keep system updated: `sudo apt-get update && sudo apt-get upgrade`
- [ ] Use strong passwords
- [ ] Enable SSH key authentication only (disable password auth)
- [ ] Keep `.env` and credentials files secure (chmod 600)
- [ ] Enable firewall (UFW)
- [ ] Set up HTTPS with Let's Encrypt
- [ ] Regular backups
- [ ] Monitor logs for suspicious activity
- [ ] Keep dependencies updated: `pip list --outdated`

---

**Deployment Complete! 🎉**

Your bot is now running in production on Digital Ocean VPS!
