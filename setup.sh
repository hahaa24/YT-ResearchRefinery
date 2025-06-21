#!/bin/bash

# YT Research Refinery Setup Script
# This script helps you set up the application for first use

set -e

echo "🎬 Welcome to YT Research Refinery Setup!"
echo "=========================================="
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first:"
    echo "   https://docs.docker.com/get-docker/"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first:"
    echo "   https://docs.docker.com/compose/install/"
    exit 1
fi

echo "✅ Docker and Docker Compose are installed"
echo ""

# Check if .env file exists
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo "✅ .env file created"
else
    echo "✅ .env file already exists"
fi

echo ""

# Get custom port
read -p "🌐 Enter the port number for the web interface (default: 8000): " APP_PORT
APP_PORT=${APP_PORT:-8000}

# Update .env file with custom port
sed -i.bak "s/APP_PORT=.*/APP_PORT=$APP_PORT/" .env
rm -f .env.bak

echo "✅ Port configured: $APP_PORT"
echo ""

# Ask about API keys
echo "🔑 API Key Configuration"
echo "========================"
echo "You'll need to configure at least one LLM provider API key."
echo ""

read -p "🤖 Which LLM provider would you like to use? (openai/anthropic/ollama): " LLM_PROVIDER
LLM_PROVIDER=${LLM_PROVIDER:-openai}

# Update .env file with LLM provider
sed -i.bak "s/LLM_PROVIDER=.*/LLM_PROVIDER=$LLM_PROVIDER/" .env
rm -f .env.bak

case $LLM_PROVIDER in
    "openai")
        echo ""
        echo "🔑 OpenAI Configuration"
        echo "Get your API key from: https://platform.openai.com/api-keys"
        read -p "Enter your OpenAI API key: " OPENAI_API_KEY
        if [ ! -z "$OPENAI_API_KEY" ]; then
            sed -i.bak "s/OPENAI_API_KEY=.*/OPENAI_API_KEY=$OPENAI_API_KEY/" .env
            rm -f .env.bak
            echo "✅ OpenAI API key configured"
        fi
        ;;
    "anthropic")
        echo ""
        echo "🔑 Anthropic Configuration"
        echo "Get your API key from: https://console.anthropic.com/"
        read -p "Enter your Anthropic API key: " ANTHROPIC_API_KEY
        if [ ! -z "$ANTHROPIC_API_KEY" ]; then
            sed -i.bak "s/ANTHROPIC_API_KEY=.*/ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY/" .env
            rm -f .env.bak
            echo "✅ Anthropic API key configured"
        fi
        ;;
    "ollama")
        echo ""
        echo "🔑 Ollama Configuration"
        echo "Make sure Ollama is running locally or provide a custom URL"
        read -p "Enter Ollama base URL (default: http://localhost:11434): " OLLAMA_BASE_URL
        OLLAMA_BASE_URL=${OLLAMA_BASE_URL:-http://localhost:11434}
        sed -i.bak "s|OLLAMA_BASE_URL=.*|OLLAMA_BASE_URL=$OLLAMA_BASE_URL|" .env
        rm -f .env.bak
        echo "✅ Ollama URL configured: $OLLAMA_BASE_URL"
        ;;
    *)
        echo "❌ Invalid LLM provider selected"
        exit 1
        ;;
esac

echo ""

# Ask about cost limit
read -p "💰 Enter maximum cost limit per operation in USD (default: 0.10): " MAX_COST_LIMIT
MAX_COST_LIMIT=${MAX_COST_LIMIT:-0.10}
sed -i.bak "s/MAX_COST_LIMIT=.*/MAX_COST_LIMIT=$MAX_COST_LIMIT/" .env
rm -f .env.bak

echo "✅ Cost limit configured: $MAX_COST_LIMIT"
echo ""

# Optional YouTube API key
echo "📺 YouTube API Key (Optional)"
echo "This is optional and only needed for additional video metadata."
echo "Get one from: https://console.cloud.google.com/"
read -p "Enter YouTube API key (or press Enter to skip): " YOUTUBE_API_KEY
if [ ! -z "$YOUTUBE_API_KEY" ]; then
    sed -i.bak "s/YOUTUBE_API_KEY=.*/YOUTUBE_API_KEY=$YOUTUBE_API_KEY/" .env
    rm -f .env.bak
    echo "✅ YouTube API key configured"
fi

echo ""

# Create output directory
echo "📁 Creating output directory..."
mkdir -p output
echo "✅ Output directory created"

echo ""

# Ask about SSL/domain configuration
echo "🔒 SSL Configuration"
echo "==================="
read -p "Do you want to configure SSL for a custom domain? (y/N): " CONFIGURE_SSL
if [[ $CONFIGURE_SSL =~ ^[Yy]$ ]]; then
    echo ""
    echo "🔒 SSL Setup"
    echo "============"
    read -p "Enter your domain name (e.g., research.yourdomain.com): " DOMAIN_NAME
    
    if [ ! -z "$DOMAIN_NAME" ]; then
        # Update .env file with SSL settings
        sed -i.bak "s/SSL_ENABLED=.*/SSL_ENABLED=true/" .env
        sed -i.bak "s/DOMAIN_NAME=.*/DOMAIN_NAME=$DOMAIN_NAME/" .env
        sed -i.bak "s|SSL_CERT_PATH=.*|SSL_CERT_PATH=/etc/letsencrypt/live/$DOMAIN_NAME/fullchain.pem|" .env
        sed -i.bak "s|SSL_KEY_PATH=.*|SSL_KEY_PATH=/etc/letsencrypt/live/$DOMAIN_NAME/privkey.pem|" .env
        rm -f .env.bak
        
        echo "✅ SSL configuration saved for domain: $DOMAIN_NAME"
        echo ""
        echo "🔒 SSL Certificate Setup Instructions:"
        echo "1. Make sure your domain $DOMAIN_NAME points to this server"
        echo "2. Install Certbot: sudo apt-get install certbot"
        echo "3. Run: sudo certbot certonly --standalone -d $DOMAIN_NAME"
        echo "4. The application will automatically use the certificates"
        echo ""
        echo "⚠️  Note: You'll need to run the SSL certificate setup before starting the application"
    fi
else
    # Disable SSL
    sed -i.bak "s/SSL_ENABLED=.*/SSL_ENABLED=false/" .env
    rm -f .env.bak
    echo "✅ SSL disabled - application will run without HTTPS"
fi

echo ""

# Final setup
echo "🚀 Starting the application..."
echo ""

# Build and start the services
echo "📦 Building Docker images..."
docker-compose build

echo ""
echo "🔄 Starting services..."
docker-compose up -d

echo ""
echo "✅ Setup complete!"
echo "=================="
echo ""
echo "🌐 Your application is now running at:"
if [[ $CONFIGURE_SSL =~ ^[Yy]$ ]] && [ ! -z "$DOMAIN_NAME" ]; then
    echo "   https://$DOMAIN_NAME"
    echo "   (Make sure SSL certificates are installed first)"
else
    echo "   http://localhost:$APP_PORT"
fi
echo ""
echo "📋 Next steps:"
echo "   1. Open the web interface in your browser"
echo "   2. Go to Settings to configure your LLM provider"
echo "   3. Start processing YouTube videos!"
echo ""
echo "🔧 Useful commands:"
echo "   - View logs: docker-compose logs -f"
echo "   - Stop services: docker-compose down"
echo "   - Restart services: docker-compose restart"
echo ""
echo "📚 For more information, see the README.md file"
echo ""
echo "🎉 Happy researching!" 