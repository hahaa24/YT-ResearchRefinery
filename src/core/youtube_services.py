import re
import logging
from typing import Optional, Dict, Any
from youtube_transcript_api import YouTubeTranscriptApi
from urllib.parse import urlparse, parse_qs

logger = logging.getLogger(__name__)


def extract_video_id(url: str) -> Optional[str]:
    """Extract YouTube video ID from various URL formats."""
    patterns = [
        r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([^&\n?#]+)',
        r'youtube\.com\/watch\?.*v=([^&\n?#]+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    return None


def get_video_info(video_id: str) -> Dict[str, Any]:
    """Get basic video information."""
    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        transcript = transcript_list.find_transcript(['en'])
        
        # Get video metadata if possible
        video_info = {
            'video_id': video_id,
            'transcript_available': True,
            'language': transcript.language,
            'language_code': transcript.language_code,
        }
        
        return video_info
    except Exception as e:
        logger.error(f"Error getting video info for {video_id}: {e}")
        return {
            'video_id': video_id,
            'transcript_available': False,
            'error': str(e)
        }


def fetch_transcript(video_id: str, language: str = 'en') -> Optional[str]:
    """Fetch transcript for a YouTube video."""
    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        
        # Try to get transcript in the specified language
        try:
            transcript = transcript_list.find_transcript([language])
        except:
            # Fallback to auto-translated English if original language not available
            transcript = transcript_list.find_transcript(['en'])
        
        # Convert transcript to text
        transcript_text = ' '.join([entry['text'] for entry in transcript.fetch()])
        
        logger.info(f"Successfully fetched transcript for video {video_id}")
        return transcript_text
        
    except Exception as e:
        logger.error(f"Error fetching transcript for video {video_id}: {e}")
        return None


def clean_transcript(transcript: str) -> str:
    """Clean transcript by removing common filler words and patterns."""
    # Remove common YouTube patterns
    patterns_to_remove = [
        r'\[.*?\]',  # Remove text in brackets (like [Music], [Applause])
        r'\(.*?\)',  # Remove text in parentheses
        r'\b(um|uh|ah|er|hmm|like|you know|i mean|basically|actually|literally)\b',
        r'\b(sponsored|advertisement|ad|promotion)\b.*?',
        r'please like and subscribe.*?',
        r'thanks for watching.*?',
        r'hit the bell icon.*?',
        r'comment below.*?',
    ]
    
    cleaned = transcript
    for pattern in patterns_to_remove:
        cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
    
    # Remove extra whitespace
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    
    return cleaned


def process_video_url(url: str, clean: bool = False) -> Dict[str, Any]:
    """Process a YouTube URL and return transcript and metadata."""
    video_id = extract_video_id(url)
    if not video_id:
        return {
            'success': False,
            'error': 'Invalid YouTube URL'
        }
    
    # Get video info
    video_info = get_video_info(video_id)
    if not video_info.get('transcript_available'):
        return {
            'success': False,
            'error': 'Transcript not available for this video',
            'video_info': video_info
        }
    
    # Fetch transcript
    transcript = fetch_transcript(video_id)
    if not transcript:
        return {
            'success': False,
            'error': 'Failed to fetch transcript',
            'video_info': video_info
        }
    
    # Clean transcript if requested
    if clean:
        transcript = clean_transcript(transcript)
    
    return {
        'success': True,
        'video_id': video_id,
        'transcript': transcript,
        'cleaned': clean,
        'video_info': video_info,
        'word_count': len(transcript.split()),
        'character_count': len(transcript)
    } 