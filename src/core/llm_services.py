import os
import logging
import tiktoken
from typing import Dict, Any, Optional, List
from litellm import completion
from .youtube_services import clean_transcript
import re

logger = logging.getLogger(__name__)


class LLMService:
    def __init__(self):
        self.provider = os.getenv('LLM_PROVIDER', 'openai')
        self.max_cost_limit = float(os.getenv('MAX_COST_LIMIT', '0.10'))
        
        # Set up API keys
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        self.anthropic_api_key = os.getenv('ANTHROPIC_API_KEY')
        self.ollama_base_url = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
        
        # Cost per 1K tokens (approximate)
        self.cost_rates = {
            'openai': {
                'gpt-4': 0.03,  # $0.03 per 1K input tokens
                'gpt-3.5-turbo': 0.0015,  # $0.0015 per 1K input tokens
            },
            'anthropic': {
                'claude-3-opus': 0.015,  # $0.015 per 1K input tokens
                'claude-3-sonnet': 0.003,  # $0.003 per 1K input tokens
                'claude-3-haiku': 0.00025,  # $0.00025 per 1K input tokens
            },
            'ollama': {
                'llama2': 0.0,  # Free for local models
                'mistral': 0.0,
                'codellama': 0.0,
            }
        }
    
    def get_model_for_provider(self) -> str:
        """Get the default model for the configured provider."""
        model_map = {
            'openai': 'gpt-3.5-turbo',
            'anthropic': 'claude-3-haiku',
            'ollama': 'llama2'
        }
        return model_map.get(self.provider, 'gpt-3.5-turbo')
    
    def count_tokens(self, text: str, model: str = None) -> int:
        """Count tokens in text using tiktoken."""
        try:
            if model is None:
                model = self.get_model_for_provider()
            
            # Map model names to encoding
            encoding_map = {
                'gpt-4': 'cl100k_base',
                'gpt-3.5-turbo': 'cl100k_base',
                'claude-3-opus': 'cl100k_base',
                'claude-3-sonnet': 'cl100k_base',
                'claude-3-haiku': 'cl100k_base',
                'llama2': 'cl100k_base',  # Fallback
            }
            
            encoding_name = encoding_map.get(model, 'cl100k_base')
            encoding = tiktoken.get_encoding(encoding_name)
            return len(encoding.encode(text))
        except Exception as e:
            logger.error(f"Error counting tokens: {e}")
            # Fallback: rough estimate (1 token ≈ 4 characters)
            return len(text) // 4
    
    def estimate_cost(self, text: str, model: str = None) -> Dict[str, Any]:
        """Estimate the cost of processing text with the specified model."""
        if model is None:
            model = self.get_model_for_provider()
        
        token_count = self.count_tokens(text, model)
        
        # Get cost rate for the model
        provider_rates = self.cost_rates.get(self.provider, {})
        cost_per_1k = provider_rates.get(model, 0.001)  # Default fallback
        
        estimated_cost = (token_count / 1000) * cost_per_1k
        
        return {
            'estimated_cost': round(estimated_cost, 4),
            'token_count': token_count,
            'provider': self.provider,
            'model': model,
            'cost_per_1k_tokens': cost_per_1k
        }
    
    def check_cost_limit(self, text: str, model: str = None) -> bool:
        """Check if the estimated cost is within the limit."""
        estimate = self.estimate_cost(text, model)
        return estimate['estimated_cost'] <= self.max_cost_limit
    
    def call_llm(self, prompt: str, model: str = None, max_tokens: int = 2000) -> Dict[str, Any]:
        """Make a call to the configured LLM provider."""
        if model is None:
            model = self.get_model_for_provider()
        
        # Check cost limit
        if not self.check_cost_limit(prompt, model):
            return {
                'success': False,
                'error': f'Estimated cost exceeds limit of ${self.max_cost_limit}'
            }
        
        try:
            # Prepare the completion call
            messages = [{"role": "user", "content": prompt}]
            
            # Set up provider-specific parameters
            if self.provider == 'ollama':
                response = completion(
                    model=model,
                    messages=messages,
                    max_tokens=max_tokens,
                    api_base=self.ollama_base_url
                )
            else:
                response = completion(
                    model=model,
                    messages=messages,
                    max_tokens=max_tokens
                )
            
            return {
                'success': True,
                'response': response.choices[0].message.content,
                'usage': response.usage.dict() if response.usage else None,
                'model': model
            }
            
        except Exception as e:
            logger.error(f"Error calling LLM: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def clean_transcript_with_llm(self, transcript: str) -> Dict[str, Any]:
        """Use LLM to clean and improve transcript quality."""
        prompt = f"""
        Please clean and improve the following YouTube video transcript. Remove:
        1. Filler words (um, uh, like, you know, etc.)
        2. Sponsorship segments and advertisements
        3. YouTube-specific phrases (like and subscribe, hit the bell, etc.)
        4. Repetitive or redundant content
        5. Non-speech elements in brackets
        
        Keep the core content and maintain readability. Return only the cleaned transcript.
        
        Transcript:
        {transcript}
        """
        
        return self.call_llm(prompt, max_tokens=len(transcript.split()) * 2)
    
    def generate_summary(self, transcript: str, video_title: str = "") -> Dict[str, Any]:
        """Generate a concise summary of the video transcript."""
        prompt = f"""
        Please provide a comprehensive summary of the following YouTube video transcript.
        
        Video Title: {video_title}
        
        Please include:
        1. Main topics and key points discussed
        2. Important insights or takeaways
        3. Any actionable advice or recommendations
        4. Overall conclusion or main message
        
        Format the summary in clear, well-structured paragraphs.
        
        Transcript:
        {transcript}
        """
        
        return self.call_llm(prompt, max_tokens=1000)
    
    def synthesize_cluster_report(self, cluster_name: str, transcripts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate a comprehensive report from multiple video transcripts."""
        # Prepare transcript summaries
        transcript_texts = []
        for i, transcript_data in enumerate(transcripts, 1):
            video_id = transcript_data.get('video_id', f'Video {i}')
            transcript = transcript_data.get('transcript', '')
            transcript_texts.append(f"Video {i} ({video_id}):\n{transcript}\n")
        
        combined_transcripts = "\n".join(transcript_texts)
        
        prompt = f"""
        Create a comprehensive research report based on the following collection of YouTube video transcripts.
        
        Research Topic: {cluster_name}
        Number of Videos: {len(transcripts)}
        
        Please structure your report with the following sections:
        
        1. **Introduction**
           - Overview of the research topic
           - Scope and methodology
        
        2. **Key Takeaways**
           - Main insights from across all videos
           - Common themes and patterns
        
        3. **Detailed Analysis**
           - Breakdown of key concepts
           - Important findings and discoveries
        
        4. **Contradictions and Debates**
           - Areas where sources disagree
           - Pro/con arguments if applicable
           - Different perspectives presented
        
        5. **Actionable Steps**
           - Practical recommendations
           - Next steps for further research
        
        6. **Conclusion**
           - Summary of findings
           - Final thoughts and implications
        
        Format the output in Markdown with proper headings, bullet points, and emphasis where appropriate.
        Use [[WikiLinks]] format for key concepts to enable knowledge graph linking.
        
        Video Transcripts:
        {combined_transcripts}
        """
        
        return self.call_llm(prompt, max_tokens=3000)
    
    def extract_keywords_for_wikilinks(self, text: str) -> List[str]:
        """Extract keywords that should be converted to WikiLinks."""
        prompt = f"""
        Extract important concepts, terms, and keywords from the following text that would be valuable as WikiLinks in a knowledge graph.
        Focus on:
        - Technical terms
        - Concepts and theories
        - Names of people, places, or organizations
        - Important ideas or methodologies
        
        Return only a comma-separated list of keywords, without explanations.
        
        Text:
        {text}
        """
        
        result = self.call_llm(prompt, max_tokens=500)
        if result['success']:
            keywords = [kw.strip() for kw in result['response'].split(',')]
            return [kw for kw in keywords if len(kw) > 2]  # Filter out very short keywords
        return []
    
    def add_wikilinks(self, text: str, keywords: List[str]) -> str:
        """Add WikiLinks to the text for the specified keywords."""
        # Sort keywords by length (longest first) to avoid partial matches
        keywords.sort(key=len, reverse=True)
        
        processed_text = text
        for keyword in keywords:
            # Create a regex pattern that matches the keyword as a whole word
            pattern = r'\b' + re.escape(keyword) + r'\b'
            replacement = f'[[{keyword}]]'
            processed_text = re.sub(pattern, replacement, processed_text, flags=re.IGNORECASE)
        
        return processed_text


# Global instance
llm_service = LLMService() 