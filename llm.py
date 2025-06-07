#!/usr/bin/env python3
import os
import logging
import tempfile
import datetime
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv
from google import genai
from google.genai import types
import time
from google.genai.types import (
    FunctionCallingConfig,
    FunctionCallingConfigMode,
    FunctionDeclaration,
    GenerateContentConfig,
    Part,
    Schema,
    Tool,
    ToolConfig,
    Type,
)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

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

def generate_news_content(
    topic: str = "latest finance and crypto news and macro economic landscape",
    model_name: str = "gemini-2.0-flash",
    temperature: float = 0.7,
    max_output_tokens: int = 512, # max token limit is 8192
    top_p: float = 0.95,
    top_k: int = 40
) -> str:
    """
    Generate news content using Google Gemini with Google Search grounding.
    
    Args:
        topic (str): The news topic to generate content about
        model_name (str): Gemini model to use
        temperature (float): Sampling temperature (0.0-1.0)
        max_output_tokens (int): Maximum output length
        top_p (float): Top-p sampling parameter
        top_k (int): Top-k sampling parameter
        
    Returns:
        str: Generated news content as a string
    
    Raises:
        Exception: If content generation fails
    """
    try:
        # Initialize API
        client = initialize_gemini_client()
        
        # Create system instruction for news anchor persona
        system_instruction = """
        You are a professional news anchor delivering a comprehensive and well-researched news broadcast. 
        Your responses should be formatted as a transcript that will be converted to speech using TTS.
        The TTS does **NOT** support emotions but you can add pauses by using . , ; ; characters to emphasize certain parts of the text.
        
        To provide the most accurate and up-to-date information:
        - Feel free to use multiple tool calls and grounding searches to gather comprehensive context
        - Research multiple sources to verify facts and present balanced perspectives
        - Incorporate relevant economic data, market trends, and expert opinions
        - Use real-time information whenever possible
        
        Guidelines for your news broadcast:
        1. Use clear, engaging language suitable for a spoken news broadcast
        2. Structure your response with a compelling introduction, detailed main points, and thoughtful conclusion
        3. Maintain a professional, informative tone throughout
        4. Do NOT include any formatting that wouldn't be spoken (like bullet points or markdown)
        5. Do NOT use phrases like "vibey music" or any audio/visual directions
        6. Do NOT include timestamps, sound effects, or music cues
        7. Do NOT use phrases like "back to you" or references to other anchors
        8. Keep sentences concise and easy to speak naturally
        9. Use natural transitions between topics
        10. End with a brief sign-off like a real news anchor would
        
        Your goal is to deliver a comprehensive, accurate, and engaging news report that sounds natural when spoken.

        Stay way from using ``` or any other formatting and do not include any citations or references.
        Further do not include exact asset prices or any other exact numbers, only use them as a reference.
        """
        
        # Create prompt for news generation
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        prompt = f"Create a comprehensive news report about {topic}. Current time: {current_time}. Make sure to cover only news from the last 24 hours."
        
        # Configure Google Search as a tool
        google_search_tool = types.Tool(
            google_search=types.GoogleSearch()
        )
        
        # Configure generation parameters
        generate_config = types.GenerateContentConfig(
            temperature=temperature,
            top_p=top_p,
            top_k=top_k,
            max_output_tokens=max_output_tokens,
            system_instruction=system_instruction,
            tools=[google_search_tool],
            # forcing function calling with mode ANY
            tool_config=ToolConfig(
                function_calling_config=FunctionCallingConfig(
                    mode=FunctionCallingConfigMode.ANY
                )
            ),
            response_mime_type='text/plain'
        )
        
        logger.info(f"Generating news content about: {topic}")
        
        # Generate content
        response = client.models.generate_content(
            model=model_name,
            contents=[prompt],
            config=generate_config
        )
        
        print(response)
        # Extract and return the generated text
        if response and hasattr(response, 'text'):
            logger.info("News content generated successfully")
            
            # Check if Google Search grounding was used
            # we want to always be grounded in search
            if hasattr(response.candidates[0], 'grounding_metadata') and response.candidates[0].grounding_metadata:
                if hasattr(response.candidates[0].grounding_metadata, 'web_search_queries') and response.candidates[0].grounding_metadata.web_search_queries:
                    logger.info(f"Google Search grounding was used with queries: {response.candidates[0].grounding_metadata.web_search_queries}")
                else:
                    logger.info("Google Search grounding was configured but no search queries were made")
                    raise Exception("Google Search grounding was configured but no search queries were made")
            else:
                logger.info("Google Search grounding was not used in the response")
                raise Exception("Google Search grounding was not used in the response")
                
            return response.text
        else:
            logger.warning("Empty response received from Gemini API")
            return "No news content could be generated at this time."
            
    except Exception as e:
        logger.error(f"Error generating news content: {str(e)}")
        raise
