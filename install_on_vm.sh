#!/bin/bash

# YT-Research-Refinery Installation Script
# This script will install and configure the YT-Research-Refinery on a fresh Ubuntu 24.04 server.
# It will install Docker, create a dedicated user, and set up the application to run as a service.

set -euo pipefail

# --- Helper Functions ---

# Function to print a formatted header
print_header() {
    echo ""
    echo "======================================================================"
    echo "=> $1"
    echo "======================================================================"
}

# Function to check if a command exists
command_exists() {
    command -v "$1" &> /dev/null
}

# --- Pre-flight Checks ---

print_header "Starting YT-Research-Refinery Installation"

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "❌ Error: This script must be run as root. Please use 'sudo'."
    exit 1
fi

# Check for Ubuntu 24.04
if ! grep -q "24.04" /etc/os-release; then
    echo "⚠️ Warning: This script is designed for Ubuntu 24.04. Your system may not be compatible."
    read -p "Do you want to continue anyway? (y/n): " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# --- Configuration ---

print_header "Configuration"

# Ask for the Git repository URL
read -p "Enter the Git repository URL for YT-Research-Refinery: " REPO_URL
if [ -z "$REPO_URL" ]; then
    echo "❌ Error: Repository URL cannot be empty."
    exit 1
fi

# Ask for the application username
read -p "Enter a username for the application [default: ytresearch]: " APP_USER
APP_USER=${APP_USER:-ytresearch}
APP_HOME="/home/$APP_USER"
APP_DIR="$APP_HOME/yt-research-refinery"

# --- System Setup ---

print_header "System Setup"

echo "📦 Updating system packages..."
apt-get update > /dev/null && apt-get upgrade -y > /dev/null
echo "✅ System packages updated."

echo "🔧 Installing required dependencies..."
apt-get install -y git curl apt-transport-https ca-certificates software-properties-common ufw > /dev/null
echo "✅ Dependencies installed."

# --- Docker Installation ---

print_header "Docker Installation"

if ! command_exists docker; then
    echo "🐳 Installing Docker..."
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
    apt-get update > /dev/null
    apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin > /dev/null
    echo "✅ Docker installed."
else
    echo "✅ Docker is already installed."
fi

echo "🚀 Starting and enabling Docker service..."
systemctl start docker
systemctl enable docker
echo "✅ Docker service is running."

# --- Application User Setup ---

print_header "Application User Setup"

if ! id "$APP_USER" &>/dev/null; then
    echo "👤 Creating application user '$APP_USER'..."
    useradd -m -s /bin/bash "$APP_USER"
    echo "✅ User '$APP_USER' created."
else
    echo "✅ User '$APP_USER' already exists."
fi

echo "➕ Adding user '$APP_USER' to the 'docker' group..."
usermod -aG docker "$APP_USER"
echo "✅ User added to docker group."

# --- Application Deployment ---

print_header "Deploying Application"

echo "📂 Cloning repository into $APP_DIR..."
if [ -d "$APP_DIR" ]; then
    echo "⚠️ Directory $APP_DIR already exists. Pulling latest changes."
    sudo -u "$APP_USER" git -C "$APP_DIR" pull
else
    sudo -u "$APP_USER" git clone "$REPO_URL" "$APP_DIR"
fi
echo "✅ Repository cloned."

echo "📝 Setting up .env configuration..."
if [ ! -f "$APP_DIR/.env" ]; then
    sudo -u "$APP_USER" cp "$APP_DIR/.env.example" "$APP_DIR/.env"
    echo "✅ .env file created from .env.example."
else
    echo "✅ .env file already exists."
fi

# --- Systemd Service Setup ---

print_header "Setting up systemd Service"

echo "🔧 Creating systemd service file..."
cat > /etc/systemd/system/yt-research-refinery.service << EOF
[Unit]
Description=YT Research Refinery
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
User=$APP_USER
Group=$APP_USER
WorkingDirectory=$APP_DIR

ExecStart=$(which docker) compose up -d --build
ExecStop=$(which docker) compose down

[Install]
WantedBy=multi-user.target
EOF

echo "🔄 Reloading systemd daemon and enabling the service..."
systemctl daemon-reload
systemctl enable yt-research-refinery.service
echo "✅ Service 'yt-research-refinery' created and enabled."


# --- Firewall Setup ---

print_header "Configuring Firewall"
ufw allow ssh > /dev/null
ufw allow 80/tcp > /dev/null
ufw allow 443/tcp > /dev/null
ufw allow 8000/tcp > /dev/null # For the app itself
ufw --force enable > /dev/null
echo "✅ Firewall configured to allow SSH, HTTP, HTTPS, and application traffic."

# --- Final Instructions ---

print_header "🎉 Installation Complete! 🎉"
echo ""
echo "The YT-Research-Refinery application has been installed."
echo ""
echo "‼️ IMPORTANT NEXT STEPS:"
echo "1. Configure the application by editing the .env file:"
echo "   sudo nano $APP_DIR/.env"
echo ""
echo "   You MUST set your LLM provider and API keys."
echo "   You can also configure the cost limit and SSL settings."
echo ""
echo "2. Once configured, start the application with:"
echo "   sudo systemctl start yt-research-refinery"
echo ""
echo "3. You can check the status and logs using:"
echo "   sudo systemctl status yt-research-refinery"
echo "   sudo docker compose -f $APP_DIR/docker-compose.yml logs -f"
echo ""
echo "4. Access the application at http://<your_server_ip>:8000"
echo ""
echo "----------------------------------------------------------------------"

# Ask to start the service
read -p "Do you want to start the service now? (y/n): " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🚀 Starting the service..."
    systemctl start yt-research-refinery
    echo "✅ Service started. It may take a few minutes for the containers to build and start."
fi

exit 0 