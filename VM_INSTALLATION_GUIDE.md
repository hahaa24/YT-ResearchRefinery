# 🖥️ VM Installation Guide

## Quick Installation on Ubuntu 24.04 VM

### Prerequisites
- Ubuntu 24.04 LTS VM
- Root access
- Internet connection
- IP: 192.168.178.17 (your VM)

### Method 1: Automated Installation (Recommended)

1. **Copy the installation script to your VM:**
   ```bash
   # On your local machine, copy the script
   scp install_on_vm.sh root@192.168.178.17:/tmp/
   ```

2. **SSH into your VM:**
   ```bash
   ssh root@192.168.178.17
   ```

3. **Run the installation script:**
   ```bash
   bash /tmp/install_on_vm.sh
   ```

4. **Follow the post-installation steps shown by the script**

### Method 2: Manual Installation

If you prefer manual installation, follow these steps:

#### 1. Update System
```bash
apt update && apt upgrade -y
```

#### 2. Install Docker
```bash
# Install required packages
apt install -y curl wget git software-properties-common apt-transport-https ca-certificates gnupg lsb-release

# Add Docker GPG key
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

# Add Docker repository
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker
apt update
apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Start and enable Docker
systemctl start docker
systemctl enable docker
```

#### 3. Create Application User
```bash
useradd -m -s /bin/bash ytresearch
usermod -aG docker ytresearch
```

#### 4. Clone Repository
```bash
mkdir -p /opt/yt-research-refinery
cd /opt/yt-research-refinery
git clone https://github.com/hahaa24/YT-ResearchRefinery.git .
chown -R ytresearch:ytresearch /opt/yt-research-refinery
```

#### 5. Configure Firewall
```bash
ufw allow ssh
ufw allow 8000/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable
```

#### 6. Create Systemd Service
```bash
cat > /etc/systemd/system/yt-research-refinery.service << 'EOF'
[Unit]
Description=YT Research Refinery
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/yt-research-refinery
ExecStart=/usr/bin/docker-compose up -d
ExecStop=/usr/bin/docker-compose down
User=ytresearch
Group=ytresearch

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable yt-research-refinery.service
```

### Post-Installation Configuration

#### 1. Switch to Application User
```bash
su - ytresearch
```

#### 2. Create Environment File
```bash
cd /opt/yt-research-refinery
cp .env.example .env
nano .env
```

#### 3. Configure Settings
Edit the `.env` file with your settings:

```bash
# Application Configuration
APP_PORT=8000
APP_HOST=0.0.0.0

# LLM Configuration
LLM_PROVIDER=openai  # or anthropic, ollama
OPENAI_API_KEY=your_openai_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here
OLLAMA_BASE_URL=http://localhost:11434

# Cost Management
MAX_COST_LIMIT=0.10

# Redis Configuration
REDIS_URL=redis://redis:6379

# Celery Configuration
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0

# YouTube Configuration (Optional)
YOUTUBE_API_KEY=your_youtube_api_key_here

# Output Configuration
OUTPUT_DIR=./output

# SSL Configuration (Optional)
SSL_ENABLED=false
SSL_CERT_PATH=/etc/letsencrypt/live/yourdomain.com/fullchain.pem
SSL_KEY_PATH=/etc/letsencrypt/live/yourdomain.com/privkey.pem
DOMAIN_NAME=yourdomain.com
```

#### 4. Start the Application
```bash
# Exit to root user
exit

# Start the service
systemctl start yt-research-refinery

# Check status
systemctl status yt-research-refinery
```

#### 5. Access the Application
Open your browser and navigate to:
```
http://192.168.178.17:8000
```

### Management Commands

#### Using the Management Script
```bash
yt-research-manage start    # Start application
yt-research-manage stop     # Stop application
yt-research-manage restart  # Restart application
yt-research-manage status   # Show status
yt-research-manage logs     # Show logs
yt-research-manage setup    # Run setup
```

#### Using Systemctl Directly
```bash
systemctl start yt-research-refinery
systemctl stop yt-research-refinery
systemctl restart yt-research-refinery
systemctl status yt-research-refinery
journalctl -u yt-research-refinery -f
```

### SSL/HTTPS Setup (Optional)

If you want to use SSL with a domain:

1. **Configure domain in .env:**
   ```bash
   SSL_ENABLED=true
   DOMAIN_NAME=yourdomain.com
   SSL_CERT_PATH=/etc/letsencrypt/live/yourdomain.com/fullchain.pem
   SSL_KEY_PATH=/etc/letsencrypt/live/yourdomain.com/privkey.pem
   ```

2. **Install Certbot:**
   ```bash
   apt install -y certbot
   ```

3. **Generate certificates:**
   ```bash
   certbot certonly --standalone -d yourdomain.com
   ```

4. **Restart the application:**
   ```bash
   systemctl restart yt-research-refinery
   ```

### Troubleshooting

#### Check Application Status
```bash
systemctl status yt-research-refinery
```

#### View Application Logs
```bash
journalctl -u yt-research-refinery -f
```

#### Check Docker Containers
```bash
docker ps
docker logs yt-research-refinery-web-app-1
docker logs yt-research-refinery-worker-1
```

#### Restart Everything
```bash
systemctl restart yt-research-refinery
```

#### Check Firewall
```bash
ufw status
```

### File Locations

- **Application:** `/opt/yt-research-refinery/`
- **Output files:** `/opt/yt-research-refinery/output/`
- **Configuration:** `/opt/yt-research-refinery/.env`
- **Service file:** `/etc/systemd/system/yt-research-refinery.service`
- **Management script:** `/usr/local/bin/yt-research-manage`

### Security Notes

- The application runs as user `ytresearch` (not root)
- Firewall is configured to allow only necessary ports
- SSL certificates are mounted read-only
- All sensitive data is stored in environment variables

### Performance Optimization

For better performance on your VM:

1. **Increase Docker memory limit** (if needed)
2. **Use SSD storage** for the output directory
3. **Configure swap space** if needed
4. **Monitor resource usage** with `htop` or `docker stats`

---

**🎬 Your YT Research Refinery is now ready for production use!** 