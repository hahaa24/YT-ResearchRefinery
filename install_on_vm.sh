#!/bin/bash

# YT Research Refinery VM Installation Script
# For Ubuntu 24.04 LTS
# Run this script as root on your VM

set -e

echo "🎬 YT Research Refinery VM Installation"
echo "======================================="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "❌ This script must be run as root"
    echo "   Please run: sudo bash install_on_vm.sh"
    exit 1
fi

echo "✅ Running as root"
echo ""

# Update system
echo "📦 Updating system packages..."
apt update && apt upgrade -y
echo "✅ System updated"
echo ""

# Install required packages
echo "📦 Installing required packages..."
apt install -y \
    curl \
    wget \
    git \
    software-properties-common \
    apt-transport-https \
    ca-certificates \
    gnupg \
    lsb-release \
    certbot \
    python3-pip \
    python3-venv \
    unzip
echo "✅ Required packages installed"
echo ""

# Install Docker
echo "🐳 Installing Docker..."
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

apt update
apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
echo "✅ Docker installed"
echo ""

# Start and enable Docker
systemctl start docker
systemctl enable docker
echo "✅ Docker service started and enabled"
echo ""

# Create application user
echo "👤 Creating application user..."
useradd -m -s /bin/bash ytresearch || echo "User already exists"
usermod -aG docker ytresearch
echo "✅ Application user created"
echo ""

# Create application directory
echo "📁 Creating application directory..."
mkdir -p /opt/yt-research-refinery
chown ytresearch:ytresearch /opt/yt-research-refinery
echo "✅ Application directory created"
echo ""

# Clone the repository
echo "📥 Cloning YT Research Refinery repository..."
cd /opt/yt-research-refinery
if [ -d ".git" ]; then
    echo "Repository already exists, pulling latest changes..."
    git pull
else
    git clone https://github.com/hahaa24/YT-ResearchRefinery.git .
fi
chown -R ytresearch:ytresearch /opt/yt-research-refinery
echo "✅ Repository cloned"
echo ""

# Create output directory
echo "📁 Creating output directory..."
mkdir -p /opt/yt-research-refinery/output
chown ytresearch:ytresearch /opt/yt-research-refinery/output
echo "✅ Output directory created"
echo ""

# Set up firewall
echo "🔥 Configuring firewall..."
ufw allow ssh
ufw allow 8000/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable
echo "✅ Firewall configured"
echo ""

# Create systemd service for auto-start
echo "🔧 Creating systemd service..."
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
echo "✅ Systemd service created and enabled"
echo ""

# Create setup script for the user
echo "📝 Creating user setup script..."
cat > /opt/yt-research-refinery/setup_user.sh << 'EOF'
#!/bin/bash

# User setup script for YT Research Refinery
# Run this as the ytresearch user

set -e

echo "🎬 YT Research Refinery User Setup"
echo "=================================="
echo ""

# Check if running as correct user
if [ "$USER" != "ytresearch" ]; then
    echo "❌ This script must be run as ytresearch user"
    echo "   Please run: sudo -u ytresearch bash setup_user.sh"
    exit 1
fi

echo "✅ Running as ytresearch user"
echo ""

cd /opt/yt-research-refinery

# Check if .env file exists
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo "✅ .env file created"
else
    echo "✅ .env file already exists"
fi

echo ""
echo "🔧 Configuration Required"
echo "========================"
echo ""
echo "Please edit the .env file to configure your settings:"
echo "  nano /opt/yt-research-refinery/.env"
echo ""
echo "Required settings:"
echo "  - LLM_PROVIDER (openai/anthropic/ollama)"
echo "  - API keys for your chosen provider"
echo "  - MAX_COST_LIMIT (default: 0.10)"
echo "  - Optional: SSL configuration for domain"
echo ""
echo "After configuration, start the application with:"
echo "  sudo systemctl start yt-research-refinery"
echo ""
echo "Check status with:"
echo "  sudo systemctl status yt-research-refinery"
echo ""
echo "View logs with:"
echo "  sudo journalctl -u yt-research-refinery -f"
echo ""
echo "Access the application at:"
echo "  http://$(hostname -I | awk '{print $1}'):8000"
echo ""
EOF

chmod +x /opt/yt-research-refinery/setup_user.sh
chown ytresearch:ytresearch /opt/yt-research-refinery/setup_user.sh
echo "✅ User setup script created"
echo ""

# Create management script
echo "📝 Creating management script..."
cat > /usr/local/bin/yt-research-manage << 'EOF'
#!/bin/bash

# YT Research Refinery Management Script
# Usage: yt-research-manage [start|stop|restart|status|logs|setup]

case "$1" in
    start)
        echo "Starting YT Research Refinery..."
        systemctl start yt-research-refinery
        ;;
    stop)
        echo "Stopping YT Research Refinery..."
        systemctl stop yt-research-refinery
        ;;
    restart)
        echo "Restarting YT Research Refinery..."
        systemctl restart yt-research-refinery
        ;;
    status)
        systemctl status yt-research-refinery
        ;;
    logs)
        journalctl -u yt-research-refinery -f
        ;;
    setup)
        echo "Running user setup..."
        sudo -u ytresearch bash /opt/yt-research-refinery/setup_user.sh
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|logs|setup}"
        echo ""
        echo "Commands:"
        echo "  start   - Start the application"
        echo "  stop    - Stop the application"
        echo "  restart - Restart the application"
        echo "  status  - Show application status"
        echo "  logs    - Show application logs"
        echo "  setup   - Run user setup script"
        exit 1
        ;;
esac
EOF

chmod +x /usr/local/bin/yt-research-manage
echo "✅ Management script created"
echo ""

# Print completion message
echo "🎉 Installation Complete!"
echo "========================"
echo ""
echo "✅ System packages installed"
echo "✅ Docker installed and configured"
echo "✅ Application user created (ytresearch)"
echo "✅ Repository cloned to /opt/yt-research-refinery"
echo "✅ Firewall configured"
echo "✅ Systemd service created"
echo "✅ Management scripts created"
echo ""
echo "📋 Next Steps:"
echo "=============="
echo ""
echo "1. Switch to the application user:"
echo "   su - ytresearch"
echo ""
echo "2. Run the user setup script:"
echo "   bash /opt/yt-research-refinery/setup_user.sh"
echo ""
echo "3. Configure your settings:"
echo "   nano /opt/yt-research-refinery/.env"
echo ""
echo "4. Start the application:"
echo "   sudo systemctl start yt-research-refinery"
echo ""
echo "5. Check status:"
echo "   sudo systemctl status yt-research-refinery"
echo ""
echo "6. Access the application:"
echo "   http://$(hostname -I | awk '{print $1}'):8000"
echo ""
echo "🔧 Management Commands:"
echo "======================"
echo "  yt-research-manage start    - Start application"
echo "  yt-research-manage stop     - Stop application"
echo "  yt-research-manage restart  - Restart application"
echo "  yt-research-manage status   - Show status"
echo "  yt-research-manage logs     - Show logs"
echo "  yt-research-manage setup    - Run setup"
echo ""
echo "📚 For more information, see:"
echo "  /opt/yt-research-refinery/README.md"
echo ""
echo "🎬 Happy researching!" 