#!/usr/bin/env python3
import os
import logging
import datetime
from dotenv import load_dotenv
from google import genai
from google.genai import types

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
DEFAULT_GEMINI_MODEL = "gemini-flash-latest"

def initialize_gemini_client():
    """
    Initialize Google Gemini API.
    
    Raises:
        ValueError: If GEMINI_API_KEY is not found in environment variables
    """
    # Load environment variables
    load_dotenv()
    
    # Get API key from environment variables
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found in environment variables")
    
    # Configure the API
    client = genai.Client(api_key=api_key)
    logger.info("Google Generative AI API initialized successfully")
    return client

def generate(
    prompt: str = "latest finance and crypto news and macro economic landscape",
    *,
    system_instruction: str | None = None,
) -> str:
    """
    Generate text using Google Gemini with Google Search grounding.

    Args:
        prompt (str): Prompt to generate content from
        model_name (str): Gemini model to use
        temperature (float): Sampling temperature (0.0-1.0)
        max_output_tokens (int): Maximum output length
        top_p (float): Top-p sampling parameter
        top_k (int): Top-k sampling parameter
        
    Returns:
        str: Generated text content
    
    Raises:
        Exception: If content generation fails
    """
    try:
        # Initialize API
        client = initialize_gemini_client()
        model_name = os.getenv("GEMINI_MODEL", DEFAULT_GEMINI_MODEL)
        
        default_system_instruction = """
        You are writing a spoken livestream segment.
        Keep the copy natural for TTS, avoid markdown and citations, and prioritize concrete developments over filler.
        Use search grounding when it materially improves accuracy.
        """
        
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        full_prompt = (
            f"Create a spoken livestream segment using this brief:\n\n{prompt}\n\n"
            f"Current time: {current_time}. Use recent information when available."
        )
        
        # Configure Google Search as a tool
        google_search_tool = types.Tool(
            google_search=types.GoogleSearch()
        )
        
        # Configure generation parameters
        generate_config = types.GenerateContentConfig(
            temperature=0.7,
            max_output_tokens=1024,
            system_instruction=system_instruction or default_system_instruction,
            tools=[google_search_tool],
            response_mime_type='text/plain'
        )
        
        logger.info("Generating segment content")
        
        # Generate content
        response = client.models.generate_content(
            model=model_name,
            contents=[full_prompt],
            config=generate_config
        )
        
        # Extract and return the generated text
        if response and hasattr(response, 'text'):
            logger.info("Segment content generated successfully")
            
            # Check if Google Search grounding was used
            if hasattr(response.candidates[0], 'grounding_metadata') and response.candidates[0].grounding_metadata:
                if hasattr(response.candidates[0].grounding_metadata, 'web_search_queries') and response.candidates[0].grounding_metadata.web_search_queries:
                    logger.info(f"Google Search grounding was used with queries: {response.candidates[0].grounding_metadata.web_search_queries}")
                else:
                    logger.info("Google Search tool was available but no search queries were made")
            else:
                logger.info("Google Search grounding was not used in the response")
                
            return response.text
        else:
            logger.warning("Empty response received from Gemini API")
            return "No segment content could be generated at this time."
            
    except Exception as e:
        logger.error(f"Error generating news content: {str(e)}")
        raise
