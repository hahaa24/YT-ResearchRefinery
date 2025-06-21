# 🎬 YT Research Refinery

A self-hostable, secure, and user-friendly web application that extracts transcripts from YouTube videos, leverages Large Language Models (LLMs) to clean and synthesize this information, and produces refined, interconnected knowledge documents in Markdown format.

## ✨ Features

### 🔧 LLM Configuration
- **Multiple Provider Support**: Configure OpenAI, Anthropic (Claude), or Ollama (local)
- **Secure API Key Management**: Environment-based configuration with no database storage
- **Cost Management**: Set maximum cost limits to prevent unexpected charges (default: $0.10)

### 📹 Single Video Processing
- **Transcript Extraction**: Automatically fetch YouTube video transcripts
- **AI-Powered Summaries**: Generate concise, comprehensive summaries
- **Optional Cleaning**: Remove sponsorships, filler words, and YouTube-specific content
- **Download Support**: Save transcripts and summaries as Markdown files
- **Real-time Progress**: Enhanced progress indicators during processing

### 🔬 Research Clusters
- **Multi-Video Analysis**: Process multiple YouTube videos on a single topic
- **State Management**: Save and resume work on research clusters
- **Intelligent Synthesis**: Generate comprehensive research reports with:
  - Introduction and methodology
  - Key takeaways and insights
  - Detailed analysis of concepts
  - Contradictions and debates
  - Actionable steps and recommendations
  - Conclusion and implications

### 📤 Output & Integration
- **Markdown Export**: All content saved in Markdown format
- **WikiLinks Support**: Automatic `[[WikiLinks]]` generation for knowledge graphs
- **Obsidian Integration**: Perfect for Obsidian vaults and knowledge management
- **Local Storage**: All files saved to `./output` directory

### 🔒 Security & SSL
- **SSL/HTTPS Support**: Built-in Let's Encrypt integration for secure deployment
- **Environment-based Configuration**: No database storage of sensitive data
- **Cost Controls**: Built-in cost limits prevent unexpected charges

## 🏗️ Architecture

### System Components
- **Web App (FastAPI)**: Modern, async Python backend with HTMX frontend
- **Worker (Celery)**: Asynchronous task processing for long-running operations
- **Cache (Redis)**: Message broker and session data storage
- **Docker & Docker Compose**: Containerized deployment for easy setup

### Technology Stack
- **Backend**: FastAPI (Python)
- **Frontend**: HTMX + Tailwind CSS
- **Task Queue**: Celery + Redis
- **LLM Integration**: LiteLLM (unified interface)
- **Containerization**: Docker & Docker Compose

## 🚀 Quick Start

### Prerequisites
- Docker and Docker Compose installed
- At least one LLM provider API key (OpenAI, Anthropic, or Ollama)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd YT-ResearchRefinery
   ```

2. **Run the setup script**
   ```bash
   ./setup.sh
   ```
   
   The setup script will:
   - Check for Docker installation
   - Create `.env` file from template
   - Configure your preferred port
   - Set up API keys
   - Configure SSL/HTTPS (optional)
   - Build and start the application

3. **Access the application**
   - Open your browser to `http://localhost:8000` (or your configured port)
   - For SSL: `https://yourdomain.com` (after certificate setup)
   - Go to Settings to configure your LLM provider
   - Start processing YouTube videos!

### Manual Setup

If you prefer manual setup:

1. **Copy environment template**
   ```bash
   cp .env.example .env
   ```

2. **Edit `.env` file**
   ```bash
   # Configure your API keys and settings
   nano .env
   ```

3. **Build and start services**
   ```bash
   docker-compose up -d
   ```

## 📖 Usage Guide

### Single Video Processing

1. **Navigate to the home page**
2. **Enter a YouTube URL** in the "Single Video Analysis" section
3. **Choose options**:
   - Check "Clean transcript" to remove filler words and sponsorships
4. **Click "Process Video"**
5. **Watch real-time progress** with enhanced progress indicators
6. **Download results** when complete

### Research Clusters

1. **Create a new cluster**:
   - Enter a cluster name
   - Add multiple YouTube URLs (one per line)
   - Choose whether to clean transcripts
   - Click "Create Research Cluster"

2. **Monitor progress**:
   - Watch real-time progress updates with detailed status
   - See which videos are being processed
   - Track overall completion percentage

3. **Generate synthesis**:
   - Once all transcripts are ready, click "Generate Synthesis Report"
   - Wait for the comprehensive report to be created

4. **Download results**:
   - Access the full research report
   - All files are automatically saved to the `./output` directory

### Settings Configuration

1. **Choose LLM Provider**:
   - **OpenAI**: Most widely supported, good performance
   - **Anthropic**: Excellent for analysis and synthesis
   - **Ollama**: Free local models, privacy-focused

2. **Configure API Keys**:
   - Get API keys from respective providers
   - Enter them securely in the settings page

3. **Set Cost Limits**:
   - Configure maximum cost per operation (default: $0.10)
   - Prevents unexpected charges

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `APP_PORT` | Web interface port | `8000` |
| `LLM_PROVIDER` | LLM provider (openai/anthropic/ollama) | `openai` |
| `OPENAI_API_KEY` | OpenAI API key | - |
| `ANTHROPIC_API_KEY` | Anthropic API key | - |
| `OLLAMA_BASE_URL` | Ollama server URL | `http://localhost:11434` |
| `MAX_COST_LIMIT` | Maximum cost per operation (USD) | `0.10` |
| `YOUTUBE_API_KEY` | YouTube API key (optional) | - |
| `SSL_ENABLED` | Enable SSL/HTTPS | `false` |
| `SSL_CERT_PATH` | SSL certificate path | - |
| `SSL_KEY_PATH` | SSL private key path | - |
| `DOMAIN_NAME` | Domain name for SSL | - |

### API Key Setup

#### OpenAI
1. Visit [OpenAI Platform](https://platform.openai.com/api-keys)
2. Create a new API key
3. Add to `.env` file: `OPENAI_API_KEY=sk-your-key-here`

#### Anthropic
1. Visit [Anthropic Console](https://console.anthropic.com/)
2. Create a new API key
3. Add to `.env` file: `ANTHROPIC_API_KEY=sk-ant-your-key-here`

#### Ollama (Local)
1. Install Ollama: https://ollama.ai/
2. Pull a model: `ollama pull llama2`
3. Start Ollama service
4. Configure in `.env`: `OLLAMA_BASE_URL=http://localhost:11434`

### SSL/HTTPS Setup

1. **Configure domain** in setup script or `.env` file
2. **Install Certbot**:
   ```bash
   sudo apt-get install certbot
   ```
3. **Generate certificates**:
   ```bash
   sudo certbot certonly --standalone -d yourdomain.com
   ```
4. **Start application** - SSL will be automatically enabled

## 📁 Project Structure

```
/
├── .env.example          # Environment template
├── .gitignore           # Git ignore rules
├── docker-compose.yml   # Docker services configuration
├── Dockerfile          # Application container
├── requirements.txt    # Python dependencies
├── setup.sh           # Interactive setup script
├── README.md          # This file
└── src/
    ├── main.py        # FastAPI application
    ├── models.py      # Pydantic data models
    ├── worker.py      # Celery tasks
    └── core/
        ├── llm_services.py    # LLM integration
        └── youtube_services.py # YouTube transcript extraction
    └── templates/
        ├── base.html         # Base template
        ├── index.html        # Main interface
        └── settings.html     # Settings page
```

## 🔒 Security & Privacy

- **No Database**: All data stored in Redis (in-memory) or local files
- **Environment Variables**: Sensitive data managed via `.env` file
- **Local Processing**: Option to use local Ollama models for complete privacy
- **Cost Controls**: Built-in cost limits prevent unexpected charges
- **SSL Support**: Built-in HTTPS support with Let's Encrypt

## 🛠️ Development

### Running in Development Mode

```bash
# Install dependencies
pip install -r requirements.txt

# Start Redis (required for Celery)
docker run -d -p 6379:6379 redis:7-alpine

# Start Celery worker
celery -A src.worker.celery worker --loglevel=info

# Start FastAPI application
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

### Adding New Features

1. **Backend**: Add routes in `src/main.py`
2. **Frontend**: Create templates in `src/templates/`
3. **Tasks**: Add Celery tasks in `src/worker.py`
4. **Services**: Extend core services in `src/core/`

## 🐛 Troubleshooting

### Common Issues

**Docker Compose fails to start**
- Check if port 8000 is already in use
- Ensure Docker and Docker Compose are installed
- Try running `docker-compose down` then `docker-compose up -d`

**LLM API calls fail**
- Verify API keys are correctly set in `.env`
- Check API key permissions and quotas
- Ensure cost limits are sufficient

**YouTube transcript extraction fails**
- Verify the video has available transcripts
- Check if the video is public and accessible
- Some videos may have disabled transcripts

**Celery tasks not processing**
- Ensure Redis is running: `docker-compose ps`
- Check worker logs: `docker-compose logs worker`
- Restart services: `docker-compose restart`

**SSL certificate issues**
- Verify domain points to server
- Check certificate paths in `.env`
- Ensure certificates are readable by Docker

### Logs and Debugging

```bash
# View all logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f web-app
docker-compose logs -f worker

# Check service status
docker-compose ps

# Restart services
docker-compose restart
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- **FastAPI** for the excellent web framework
- **HTMX** for dynamic UI without complex JavaScript
- **LiteLLM** for unified LLM provider interface
- **YouTube Transcript API** for transcript extraction
- **Celery** for asynchronous task processing

## 📞 Support

For issues and questions:
1. Check the troubleshooting section
2. Review the logs for error messages
3. Open an issue on GitHub with detailed information

---

**Happy researching! 🎬📚** 