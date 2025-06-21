import os
import json
import logging
import redis
from datetime import datetime
from celery import Celery
from typing import Dict, Any, List
from .core.youtube_services import process_video_url
from .core.llm_services import llm_service

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Celery
celery = Celery('yt_research_refinery')
celery.conf.update(
    broker_url=os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0'),
    result_backend=os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0'),
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
)

# Initialize Redis
redis_client = redis.Redis.from_url(os.getenv('REDIS_URL', 'redis://localhost:6379'))


@celery.task(bind=True)
def generate_single_summary(self, video_url: str, clean_transcript: bool = False) -> Dict[str, Any]:
    """Process a single video and generate a summary."""
    try:
        self.update_state(state='PROGRESS', meta={'status': 'Fetching transcript...'})
        
        # Process video URL
        result = process_video_url(video_url, clean_transcript)
        if not result['success']:
            return {
                'success': False,
                'error': result['error']
            }
        
        self.update_state(state='PROGRESS', meta={'status': 'Generating summary...'})
        
        # Generate summary using LLM
        summary_result = llm_service.generate_summary(
            result['transcript'],
            f"Video {result['video_id']}"
        )
        
        if not summary_result['success']:
            return {
                'success': False,
                'error': summary_result['error']
            }
        
        # Prepare final result
        final_result = {
            'success': True,
            'video_id': result['video_id'],
            'transcript': result['transcript'],
            'summary': summary_result['response'],
            'word_count': result['word_count'],
            'character_count': result['character_count'],
            'cleaned': clean_transcript,
            'usage': summary_result.get('usage'),
            'model': summary_result.get('model')
        }
        
        # Save to output directory
        save_single_video_result(final_result)
        
        return final_result
        
    except Exception as e:
        logger.error(f"Error in generate_single_summary: {e}")
        return {
            'success': False,
            'error': str(e)
        }


@celery.task(bind=True)
def process_cluster_transcripts(self, session_id: str, cluster_name: str, urls: List[str], clean_transcripts: bool = False) -> Dict[str, Any]:
    """Process all transcripts for a research cluster."""
    try:
        # Initialize cluster state
        cluster_state = {
            'session_id': session_id,
            'name': cluster_name,
            'urls': urls,
            'status': 'processing',
            'transcripts': {},
            'cleaned_transcripts': {},
            'summary': None,
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
        
        # Save initial state
        save_cluster_state(session_id, cluster_state)
        
        total_urls = len(urls)
        processed_count = 0
        
        for i, url in enumerate(urls):
            self.update_state(
                state='PROGRESS', 
                meta={
                    'status': f'Processing video {i+1}/{total_urls}',
                    'current': i + 1,
                    'total': total_urls
                }
            )
            
            # Process video
            result = process_video_url(url, clean_transcripts)
            
            if result['success']:
                video_id = result['video_id']
                cluster_state['transcripts'][video_id] = result['transcript']
                
                if clean_transcripts:
                    cluster_state['cleaned_transcripts'][video_id] = result['transcript']
                
                processed_count += 1
            else:
                logger.warning(f"Failed to process video {url}: {result['error']}")
            
            # Update cluster state
            cluster_state['updated_at'] = datetime.now().isoformat()
            save_cluster_state(session_id, cluster_state)
        
        # Update final state
        cluster_state['status'] = 'transcripts_ready'
        cluster_state['updated_at'] = datetime.now().isoformat()
        save_cluster_state(session_id, cluster_state)
        
        return {
            'success': True,
            'session_id': session_id,
            'processed_count': processed_count,
            'total_count': total_urls,
            'status': 'transcripts_ready'
        }
        
    except Exception as e:
        logger.error(f"Error in process_cluster_transcripts: {e}")
        return {
            'success': False,
            'error': str(e)
        }


@celery.task(bind=True)
def clean_cluster_transcripts(self, session_id: str) -> Dict[str, Any]:
    """Clean transcripts in a cluster using LLM."""
    try:
        # Load cluster state
        cluster_state = load_cluster_state(session_id)
        if not cluster_state:
            return {
                'success': False,
                'error': 'Cluster not found'
            }
        
        self.update_state(state='PROGRESS', meta={'status': 'Cleaning transcripts...'})
        
        # Clean each transcript
        for video_id, transcript in cluster_state['transcripts'].items():
            clean_result = llm_service.clean_transcript_with_llm(transcript)
            
            if clean_result['success']:
                cluster_state['cleaned_transcripts'][video_id] = clean_result['response']
            else:
                logger.warning(f"Failed to clean transcript for {video_id}: {clean_result['error']}")
                # Fallback to original transcript
                cluster_state['cleaned_transcripts'][video_id] = transcript
        
        # Update cluster state
        cluster_state['status'] = 'cleaned_ready'
        cluster_state['updated_at'] = datetime.now().isoformat()
        save_cluster_state(session_id, cluster_state)
        
        return {
            'success': True,
            'session_id': session_id,
            'status': 'cleaned_ready'
        }
        
    except Exception as e:
        logger.error(f"Error in clean_cluster_transcripts: {e}")
        return {
            'success': False,
            'error': str(e)
        }


@celery.task(bind=True)
def synthesize_cluster_report(self, session_id: str) -> Dict[str, Any]:
    """Generate final synthesis report for a cluster."""
    try:
        # Load cluster state
        cluster_state = load_cluster_state(session_id)
        if not cluster_state:
            return {
                'success': False,
                'error': 'Cluster not found'
            }
        
        self.update_state(state='PROGRESS', meta={'status': 'Generating synthesis report...'})
        
        # Prepare transcripts for synthesis
        transcripts_to_use = cluster_state.get('cleaned_transcripts', cluster_state['transcripts'])
        
        # Convert to list format for synthesis
        transcript_list = []
        for video_id, transcript in transcripts_to_use.items():
            transcript_list.append({
                'video_id': video_id,
                'transcript': transcript
            })
        
        # Generate synthesis report
        synthesis_result = llm_service.synthesize_cluster_report(
            cluster_state['name'],
            transcript_list
        )
        
        if not synthesis_result['success']:
            return {
                'success': False,
                'error': synthesis_result['error']
            }
        
        # Extract keywords and add WikiLinks
        keywords = llm_service.extract_keywords_for_wikilinks(synthesis_result['response'])
        final_report = llm_service.add_wikilinks(synthesis_result['response'], keywords)
        
        # Update cluster state
        cluster_state['summary'] = final_report
        cluster_state['status'] = 'completed'
        cluster_state['updated_at'] = datetime.now().isoformat()
        save_cluster_state(session_id, cluster_state)
        
        # Save report to output directory
        save_cluster_report(session_id, cluster_state)
        
        return {
            'success': True,
            'session_id': session_id,
            'status': 'completed',
            'report': final_report,
            'keywords': keywords
        }
        
    except Exception as e:
        logger.error(f"Error in synthesize_cluster_report: {e}")
        return {
            'success': False,
            'error': str(e)
        }


def save_cluster_state(session_id: str, state: Dict[str, Any]) -> None:
    """Save cluster state to Redis."""
    try:
        redis_client.setex(
            f"cluster:{session_id}",
            3600 * 24 * 7,  # 7 days TTL
            json.dumps(state)
        )
    except Exception as e:
        logger.error(f"Error saving cluster state: {e}")


def load_cluster_state(session_id: str) -> Dict[str, Any]:
    """Load cluster state from Redis."""
    try:
        data = redis_client.get(f"cluster:{session_id}")
        if data:
            return json.loads(data)
        return None
    except Exception as e:
        logger.error(f"Error loading cluster state: {e}")
        return None


def save_single_video_result(result: Dict[str, Any]) -> None:
    """Save single video result to output directory."""
    try:
        output_dir = os.getenv('OUTPUT_DIR', './output')
        os.makedirs(output_dir, exist_ok=True)
        
        video_id = result['video_id']
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Save transcript
        transcript_filename = f"{output_dir}/{video_id}_transcript_{timestamp}.md"
        with open(transcript_filename, 'w', encoding='utf-8') as f:
            f.write(f"# Transcript: {video_id}\n\n")
            f.write(f"**Generated:** {datetime.now().isoformat()}\n")
            f.write(f"**Word Count:** {result['word_count']}\n")
            f.write(f"**Character Count:** {result['character_count']}\n")
            f.write(f"**Cleaned:** {result['cleaned']}\n\n")
            f.write("## Transcript\n\n")
            f.write(result['transcript'])
        
        # Save summary
        summary_filename = f"{output_dir}/{video_id}_summary_{timestamp}.md"
        with open(summary_filename, 'w', encoding='utf-8') as f:
            f.write(f"# Summary: {video_id}\n\n")
            f.write(f"**Generated:** {datetime.now().isoformat()}\n")
            f.write(f"**Model:** {result.get('model', 'Unknown')}\n\n")
            f.write("## Summary\n\n")
            f.write(result['summary'])
        
        logger.info(f"Saved results for video {video_id}")
        
    except Exception as e:
        logger.error(f"Error saving single video result: {e}")


def save_cluster_report(session_id: str, cluster_state: Dict[str, Any]) -> None:
    """Save cluster report to output directory."""
    try:
        output_dir = os.getenv('OUTPUT_DIR', './output')
        os.makedirs(output_dir, exist_ok=True)
        
        cluster_name = cluster_state['name']
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Create sanitized filename
        safe_name = "".join(c for c in cluster_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
        safe_name = safe_name.replace(' ', '_')
        
        filename = f"{output_dir}/{safe_name}_cluster_report_{timestamp}.md"
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(f"# Research Report: {cluster_name}\n\n")
            f.write(f"**Generated:** {datetime.now().isoformat()}\n")
            f.write(f"**Session ID:** {session_id}\n")
            f.write(f"**Videos Processed:** {len(cluster_state['transcripts'])}\n\n")
            f.write("---\n\n")
            f.write(cluster_state['summary'])
        
        logger.info(f"Saved cluster report for {cluster_name}")
        
    except Exception as e:
        logger.error(f"Error saving cluster report: {e}")


def get_all_clusters() -> List[Dict[str, Any]]:
    """Get all active clusters from Redis."""
    try:
        clusters = []
        for key in redis_client.scan_iter("cluster:*"):
            session_id = key.decode('utf-8').split(':', 1)[1]
            state = load_cluster_state(session_id)
            if state:
                clusters.append(state)
        return clusters
    except Exception as e:
        logger.error(f"Error getting all clusters: {e}")
        return [] 