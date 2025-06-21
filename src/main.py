import os
import uuid
import logging
from datetime import datetime
from typing import List, Dict, Any
from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError
from dotenv import load_dotenv

from .models import Settings, VideoRequest, ClusterRequest, TaskResult
from .core.llm_services import llm_service
from .core.youtube_services import process_video_url
from .worker import (
    generate_single_summary, 
    process_cluster_transcripts,
    clean_cluster_transcripts,
    synthesize_cluster_report,
    get_all_clusters,
    load_cluster_state
)

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="YT Research Refinery", version="1.0.0")

# Templates
templates = Jinja2Templates(directory="src/templates")

# Global settings (in production, this should be stored in a database)
current_settings = Settings()


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Main page with the application interface."""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    """Settings page for LLM configuration."""
    return templates.TemplateResponse("settings.html", {
        "request": request,
        "settings": current_settings
    })


@app.post("/settings")
async def update_settings(
    request: Request,
    llm_provider: str = Form(...),
    openai_api_key: str = Form(None),
    anthropic_api_key: str = Form(None),
    ollama_base_url: str = Form(None),
    max_cost_limit: float = Form(0.10),
    youtube_api_key: str = Form(None)
):
    """Update application settings."""
    try:
        # Update global settings
        current_settings.llm_provider = llm_provider
        current_settings.openai_api_key = openai_api_key
        current_settings.anthropic_api_key = anthropic_api_key
        current_settings.ollama_base_url = ollama_base_url
        current_settings.max_cost_limit = max_cost_limit
        current_settings.youtube_api_key = youtube_api_key
        
        # Update environment variables
        os.environ['LLM_PROVIDER'] = llm_provider
        if openai_api_key:
            os.environ['OPENAI_API_KEY'] = openai_api_key
        if anthropic_api_key:
            os.environ['ANTHROPIC_API_KEY'] = anthropic_api_key
        if ollama_base_url:
            os.environ['OLLAMA_BASE_URL'] = ollama_base_url
        os.environ['MAX_COST_LIMIT'] = str(max_cost_limit)
        if youtube_api_key:
            os.environ['YOUTUBE_API_KEY'] = youtube_api_key
        
        return HTMLResponse(
            '<div class="bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded">'
            'Settings saved successfully!</div>'
        )
    except Exception as e:
        logger.error(f"Error updating settings: {e}")
        return HTMLResponse(
            '<div class="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">'
            f'Error saving settings: {str(e)}</div>'
        )


@app.post("/process-single-video")
async def process_single_video(
    request: Request,
    url: str = Form(...),
    clean_transcript: bool = Form(False)
):
    """Process a single video and generate summary."""
    try:
        # Validate URL
        if not url.startswith(('http://', 'https://')):
            return HTMLResponse(
                '<div class="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">'
                'Please enter a valid URL</div>'
            )
        
        # Start Celery task
        task = generate_single_summary.delay(url, clean_transcript)
        
        return HTMLResponse(
            f'<div class="bg-blue-100 border border-blue-400 text-blue-700 px-4 py-3 rounded">'
            f'Processing video... Task ID: {task.id}</div>'
            f'<div id="task-result" hx-get="/task-status/{task.id}" hx-trigger="load, every 2s" hx-swap="innerHTML"></div>'
        )
        
    except Exception as e:
        logger.error(f"Error processing single video: {e}")
        return HTMLResponse(
            '<div class="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">'
            f'Error processing video: {str(e)}</div>'
        )


@app.get("/task-status/{task_id}")
async def get_task_status(task_id: str):
    """Get the status of a Celery task."""
    try:
        from celery.result import AsyncResult
        task_result = AsyncResult(task_id)
        
        if task_result.ready():
            if task_result.successful():
                result = task_result.result
                if result['success']:
                    return HTMLResponse(
                        f'<div class="bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded mb-4">'
                        f'Processing completed successfully!</div>'
                        f'<div class="bg-white border rounded p-4">'
                        f'<h3 class="font-semibold mb-2">Summary</h3>'
                        f'<p class="text-gray-700 mb-4">{result["summary"]}</p>'
                        f'<div class="text-sm text-gray-500 mb-4">'
                        f'Word count: {result["word_count"]} | '
                        f'Character count: {result["character_count"]} | '
                        f'Model: {result.get("model", "Unknown")}</div>'
                        f'<a href="/download-transcript/{result["video_id"]}" '
                        f'class="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700">Download Transcript</a> '
                        f'<a href="/download-summary/{result["video_id"]}" '
                        f'class="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700">Download Summary</a>'
                        f'</div>'
                    )
                else:
                    return HTMLResponse(
                        f'<div class="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">'
                        f'Error: {result["error"]}</div>'
                    )
            else:
                return HTMLResponse(
                    f'<div class="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">'
                    f'Task failed: {task_result.info}</div>'
                )
        else:
            # Task is still running
            meta = task_result.info or {}
            status = meta.get('status', 'Processing...')
            return HTMLResponse(
                f'<div class="bg-blue-100 border border-blue-400 text-blue-700 px-4 py-3 rounded">'
                f'{status}</div>'
            )
            
    except Exception as e:
        logger.error(f"Error getting task status: {e}")
        return HTMLResponse(
            f'<div class="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">'
            f'Error checking task status: {str(e)}</div>'
        )


@app.post("/create-cluster")
async def create_cluster(
    request: Request,
    name: str = Form(...),
    urls: str = Form(...),
    clean_transcripts: bool = Form(False)
):
    """Create a new research cluster."""
    try:
        # Parse URLs
        url_list = [url.strip() for url in urls.split('\n') if url.strip()]
        
        if not url_list:
            return HTMLResponse(
                '<div class="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">'
                'Please provide at least one URL</div>'
            )
        
        # Validate URLs
        for url in url_list:
            if not url.startswith(('http://', 'https://')):
                return HTMLResponse(
                    '<div class="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">'
                    f'Invalid URL: {url}</div>'
                )
        
        # Generate session ID
        session_id = str(uuid.uuid4())
        
        # Start Celery task
        task = process_cluster_transcripts.delay(session_id, name, url_list, clean_transcripts)
        
        return HTMLResponse(
            f'<div class="bg-blue-100 border border-blue-400 text-blue-700 px-4 py-3 rounded">'
            f'Creating research cluster "{name}"... Task ID: {task.id}</div>'
            f'<div id="cluster-task-result" hx-get="/cluster-task-status/{task.id}" hx-trigger="load, every 3s" hx-swap="innerHTML"></div>'
        )
        
    except Exception as e:
        logger.error(f"Error creating cluster: {e}")
        return HTMLResponse(
            '<div class="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">'
            f'Error creating cluster: {str(e)}</div>'
        )


@app.get("/cluster-task-status/{task_id}")
async def get_cluster_task_status(task_id: str):
    """Get the status of a cluster processing task."""
    try:
        from celery.result import AsyncResult
        task_result = AsyncResult(task_id)
        
        if task_result.ready():
            if task_result.successful():
                result = task_result.result
                if result['success']:
                    session_id = result['session_id']
                    return HTMLResponse(
                        f'<div class="bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded mb-4">'
                        f'Cluster processing completed! Processed {result["processed_count"]}/{result["total_count"]} videos.</div>'
                        f'<div class="bg-white border rounded p-4">'
                        f'<h3 class="font-semibold mb-2">Next Steps</h3>'
                        f'<p class="text-gray-700 mb-4">Your research cluster is ready for synthesis.</p>'
                        f'<button hx-post="/synthesize-cluster/{session_id}" '
                        f'hx-target="#cluster-task-result" '
                        f'class="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700">'
                        f'Generate Synthesis Report</button>'
                        f'</div>'
                    )
                else:
                    return HTMLResponse(
                        f'<div class="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">'
                        f'Error: {result["error"]}</div>'
                    )
            else:
                return HTMLResponse(
                    f'<div class="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">'
                    f'Task failed: {task_result.info}</div>'
                )
        else:
            # Task is still running
            meta = task_result.info or {}
            status = meta.get('status', 'Processing cluster...')
            current = meta.get('current', 0)
            total = meta.get('total', 0)
            
            progress_html = ""
            if current > 0 and total > 0:
                progress_percent = (current / total) * 100
                progress_html = f'<div class="w-full bg-gray-200 rounded-full h-2.5 mb-2">'
                progress_html += f'<div class="bg-blue-600 h-2.5 rounded-full" style="width: {progress_percent}%"></div></div>'
                progress_html += f'<p class="text-sm text-gray-600">{current}/{total} videos processed</p>'
            
            return HTMLResponse(
                f'<div class="bg-blue-100 border border-blue-400 text-blue-700 px-4 py-3 rounded">'
                f'{status}</div>'
                f'{progress_html}'
            )
            
    except Exception as e:
        logger.error(f"Error getting cluster task status: {e}")
        return HTMLResponse(
            f'<div class="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">'
            f'Error checking task status: {str(e)}</div>'
        )


@app.post("/synthesize-cluster/{session_id}")
async def synthesize_cluster(session_id: str):
    """Generate synthesis report for a cluster."""
    try:
        # Start synthesis task
        task = synthesize_cluster_report.delay(session_id)
        
        return HTMLResponse(
            f'<div class="bg-blue-100 border border-blue-400 text-blue-700 px-4 py-3 rounded">'
            f'Generating synthesis report... Task ID: {task.id}</div>'
            f'<div id="synthesis-result" hx-get="/synthesis-task-status/{task.id}" hx-trigger="load, every 3s" hx-swap="innerHTML"></div>'
        )
        
    except Exception as e:
        logger.error(f"Error starting synthesis: {e}")
        return HTMLResponse(
            f'<div class="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">'
            f'Error starting synthesis: {str(e)}</div>'
        )


@app.get("/synthesis-task-status/{task_id}")
async def get_synthesis_task_status(task_id: str):
    """Get the status of a synthesis task."""
    try:
        from celery.result import AsyncResult
        task_result = AsyncResult(task_id)
        
        if task_result.ready():
            if task_result.successful():
                result = task_result.result
                if result['success']:
                    return HTMLResponse(
                        f'<div class="bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded mb-4">'
                        f'Synthesis report generated successfully!</div>'
                        f'<div class="bg-white border rounded p-4">'
                        f'<h3 class="font-semibold mb-2">Report Preview</h3>'
                        f'<div class="max-h-64 overflow-y-auto mb-4 text-sm">'
                        f'{result["report"][:500]}...</div>'
                        f'<a href="/download-cluster-report/{result["session_id"]}" '
                        f'class="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700">'
                        f'Download Full Report</a>'
                        f'</div>'
                    )
                else:
                    return HTMLResponse(
                        f'<div class="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">'
                        f'Error: {result["error"]}</div>'
                    )
            else:
                return HTMLResponse(
                    f'<div class="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">'
                    f'Task failed: {task_result.info}</div>'
                )
        else:
            # Task is still running
            meta = task_result.info or {}
            status = meta.get('status', 'Generating synthesis report...')
            return HTMLResponse(
                f'<div class="bg-blue-100 border border-blue-400 text-blue-700 px-4 py-3 rounded">'
                f'{status}</div>'
            )
            
    except Exception as e:
        logger.error(f"Error getting synthesis task status: {e}")
        return HTMLResponse(
            f'<div class="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">'
            f'Error checking task status: {str(e)}</div>'
        )


@app.get("/active-clusters")
async def get_active_clusters():
    """Get all active research clusters."""
    try:
        clusters = get_all_clusters()
        
        if not clusters:
            return HTMLResponse(
                '<div class="text-center py-8 text-gray-500">No active research clusters found.</div>'
            )
        
        html = '<div class="space-y-4">'
        for cluster in clusters:
            status_color = {
                'pending': 'bg-yellow-100 text-yellow-800',
                'processing': 'bg-blue-100 text-blue-800',
                'transcripts_ready': 'bg-green-100 text-green-800',
                'cleaned_ready': 'bg-green-100 text-green-800',
                'completed': 'bg-green-100 text-green-800',
                'failed': 'bg-red-100 text-red-800'
            }.get(cluster['status'], 'bg-gray-100 text-gray-800')
            
            html += f'''
            <div class="border rounded p-4">
                <div class="flex justify-between items-start mb-2">
                    <h3 class="font-semibold">{cluster['name']}</h3>
                    <span class="px-2 py-1 rounded text-xs {status_color}">{cluster['status']}</span>
                </div>
                <p class="text-sm text-gray-600 mb-2">Videos: {len(cluster['urls'])}</p>
                <p class="text-sm text-gray-600 mb-2">Created: {cluster['created_at'][:10]}</p>
                <p class="text-sm text-gray-600">Updated: {cluster['updated_at'][:10]}</p>
            </div>
            '''
        
        html += '</div>'
        return HTMLResponse(html)
        
    except Exception as e:
        logger.error(f"Error getting active clusters: {e}")
        return HTMLResponse(
            f'<div class="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">'
            f'Error loading clusters: {str(e)}</div>'
        )


@app.get("/download-transcript/{video_id}")
async def download_transcript(video_id: str):
    """Download transcript for a video."""
    # This would typically serve a file from the output directory
    # For now, return a placeholder response
    return HTMLResponse(
        f'<div class="bg-blue-100 border border-blue-400 text-blue-700 px-4 py-3 rounded">'
        f'Transcript for {video_id} would be downloaded here.</div>'
    )


@app.get("/download-summary/{video_id}")
async def download_summary(video_id: str):
    """Download summary for a video."""
    # This would typically serve a file from the output directory
    # For now, return a placeholder response
    return HTMLResponse(
        f'<div class="bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded">'
        f'Summary for {video_id} would be downloaded here.</div>'
    )


@app.get("/download-cluster-report/{session_id}")
async def download_cluster_report(session_id: str):
    """Download cluster report."""
    # This would typically serve a file from the output directory
    # For now, return a placeholder response
    return HTMLResponse(
        f'<div class="bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded">'
        f'Cluster report for session {session_id} would be downloaded here.</div>'
    )


if __name__ == "__main__":
    import uvicorn
    
    # Check if SSL is enabled
    ssl_enabled = os.getenv('SSL_ENABLED', 'false').lower() == 'true'
    ssl_cert_path = os.getenv('SSL_CERT_PATH')
    ssl_key_path = os.getenv('SSL_KEY_PATH')
    
    if ssl_enabled and ssl_cert_path and ssl_key_path:
        # Start with SSL
        uvicorn.run(
            app, 
            host="0.0.0.0", 
            port=8000,
            ssl_certfile=ssl_cert_path,
            ssl_keyfile=ssl_key_path
        )
    else:
        # Start without SSL
        uvicorn.run(app, host="0.0.0.0", port=8000) 