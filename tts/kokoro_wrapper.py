#!/usr/bin/env python3
"""
Kokoro TTS Wrapper

A simple wrapper for the Kokoro TTS system that provides an easy-to-use interface
for text-to-speech conversion with support for different voices and long text chunking.
"""

import os
import re
import torch
import soundfile as sf
import numpy as np
from pathlib import Path
from typing import Optional, List, Union

# Import Kokoro TTS modules
from tts.kokoro import kokoro
from tts.kokoro import models

class KokoroTTS:
    """
    Wrapper for Kokoro TTS that provides an easy-to-use interface for text-to-speech
    conversion with support for different voices and long text chunking.
    """
    
    def __init__(self, model_dir: Optional[str] = None, device: str = 'cuda' if torch.cuda.is_available() else 'cpu'):
        """
        Initialize the Kokoro TTS system.
        
        Args:
            model_dir: Directory containing the Kokoro model files. If None, uses the default
                       directory in the package.
            device: Device to use for inference ('cuda' or 'cpu').
        """
        self.device = device
        
        # Set default model directory if not provided
        if model_dir is None:
            self.model_dir = Path(os.path.dirname(os.path.abspath(__file__))) / 'kokoro'
        else:
            self.model_dir = Path(model_dir)
        
        # Initialize Kokoro TTS
        self.model_path = self.model_dir / 'kokoro-v0_19.pth'
        self.config_path = self.model_dir / 'config.json'
        
        print(f"Initializing Kokoro TTS with model: {self.model_path}")
        print(f"Using device: {self.device}")
        
        # Load the model
        self.model = models.build_model(str(self.model_path), device=self.device)
        
        # Map of voice names to file paths
        self.voice_map = {
            'default': 'af_bella.pt',
            'bella': 'af_bella.pt',
            'sarah': 'af_sarah.pt',
            'george': 'bm_george.pt',
            'michael': 'am_michael.pt',
            'neutral': 'af.pt'
        }
        
        # Load available voices
        self.voices_dir = self.model_dir / 'voices'
        self._validate_voices()
        
        print(f"Available voices: {', '.join(self.voice_map.keys())}")
    
    def _validate_voices(self):
        """Validate that all voice files exist."""
        for voice_name, voice_file in self.voice_map.items():
            voice_path = self.voices_dir / voice_file
            if not voice_path.exists():
                print(f"Warning: Voice file for '{voice_name}' not found at {voice_path}")
    
    def _get_voice_path(self, voice: str) -> str:
        """Get the path to the voice file."""
        if voice not in self.voice_map:
            print(f"Warning: Voice '{voice}' not found. Using default voice 'bella'.")
            voice = 'bella'
        
        voice_file = self.voice_map[voice]
        return str(self.voices_dir / voice_file)
    
    def _load_voice(self, voice: str):
        """Load the voice file and return the voicepack."""
        voice_path = self._get_voice_path(voice)
        try:
            return torch.load(voice_path, weights_only=True).to(self.device)
        except Exception as e:
            print(f"Error loading voice file: {str(e)}")
            return None
    
    def _chunk_text(self, text: str, max_length: int = 300) -> List[str]:
        """
        Split long text into smaller chunks for better TTS processing.
        
        Args:
            text: The text to split into chunks.
            max_length: Maximum length of each chunk.
            
        Returns:
            List of text chunks.
        """
        # Clean and normalize the text
        text = text.strip()
        
        # Simple chunking based on punctuation
        chunks = []
        current_chunk = ""
        
        # Split by sentences (roughly) using common punctuation
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        for sentence in sentences:
            # If adding this sentence would exceed max_length, start a new chunk
            if len(current_chunk) + len(sentence) > max_length and current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = sentence
            else:
                # Add to current chunk with a space if needed
                if current_chunk and not current_chunk.endswith(" "):
                    current_chunk += " "
                current_chunk += sentence
        
        # Add the last chunk if it's not empty
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def speak(self, text: str, voice: str = 'bella', output_file: Optional[str] = None, 
              sample_rate: int = 24000) -> Union[np.ndarray, None]:
        """
        Convert text to speech using Kokoro TTS.
        
        Args:
            text: The text to convert to speech.
            voice: The voice to use for synthesis.
            output_file: Path to save the audio file. If None, returns the audio array.
            sample_rate: Sample rate of the output audio.
            
        Returns:
            If output_file is None, returns the audio array. Otherwise, returns None.
        """
        if not text or not text.strip():
            print("Warning: Empty text provided. Nothing to synthesize.")
            return None
        
        # Clean the text
        text = text.strip()
        
        # Load the voice
        voicepack = self._load_voice(voice)
        if voicepack is None:
            return None
        
        # Generate audio
        try:
            # Determine language based on voice
            lang = 'a'  # Default to American English
            if voice in ['sarah', 'george']:
                lang = 'b'  # British English
            
            result = kokoro.generate(self.model, text, voicepack, lang=lang)
            if result is None:
                print("Error: Failed to generate audio.")
                return None
                
            audio, phonemes = result
            print(f"Phonemes used: {phonemes}")
            
            # Save to file if output_file is provided
            if output_file:
                os.makedirs(os.path.dirname(os.path.abspath(output_file)), exist_ok=True)
                sf.write(output_file, audio, sample_rate)
                print(f"Audio saved to: {output_file}")
                return None
            
            return audio
        
        except Exception as e:
            print(f"Error synthesizing text: {str(e)}")
            return None
    
    def speak_long_text(self, text: str, voice: str = 'bella', output_file: Optional[str] = None,
                        sample_rate: int = 24000, chunk_size: int = 300) -> Union[np.ndarray, None]:
        """
        Convert long text to speech by chunking it into smaller pieces.
        
        Args:
            text: The long text to convert to speech.
            voice: The voice to use for synthesis.
            output_file: Path to save the audio file. If None, returns the audio array.
            sample_rate: Sample rate of the output audio.
            chunk_size: Maximum size of each text chunk in characters.
            
        Returns:
            If output_file is None, returns the concatenated audio array. Otherwise, returns None.
        """
        if not text or not text.strip():
            print("Warning: Empty text provided. Nothing to synthesize.")
            return None
        
        # Clean the text
        text = text.strip()
        
        # Load the voice
        voicepack = self._load_voice(voice)
        if voicepack is None:
            return None
            
        # Split text into chunks
        chunks = self._chunk_text(text, chunk_size)
        print(f"Split text into {len(chunks)} chunks")
        
        # Process each chunk and combine the audio
        all_audio = []
        
        # Determine language based on voice
        lang = 'a'  # Default to American English
        if voice in ['sarah', 'george']:
            lang = 'b'  # British English
            
        for i, chunk in enumerate(chunks):
            print(f"Processing chunk {i+1}/{len(chunks)}")
            try:
                result = kokoro.generate(self.model, chunk, voicepack, lang=lang)
                if result is None:
                    print(f"Warning: Failed to generate audio for chunk {i+1}")
                    continue
                    
                audio, phonemes = result
                all_audio.append(audio)
            except Exception as e:
                print(f"Error processing chunk {i+1}: {str(e)}")
        
        if not all_audio:
            print("Error: Failed to generate any audio.")
            return None
            
        # Combine all audio chunks
        combined_audio = np.concatenate(all_audio)
        
        # Save to file if output_file is provided
        if output_file:
            os.makedirs(os.path.dirname(os.path.abspath(output_file)), exist_ok=True)
            sf.write(output_file, combined_audio, sample_rate)
            print(f"Audio saved to: {output_file}")
            return None
        
        return combined_audio
    
    def list_available_voices(self) -> List[str]:
        """
        List all available voices.
        
        Returns:
            List of available voice names.
        """
        return list(self.voice_map.keys())


if __name__ == "__main__":
    # Simple test
    tts = KokoroTTS()
    tts.speak_long_text("Hello world! This is a test of the Kokoro TTS system.", output_file="test.wav")
    print("Test complete. Check test.wav for output.")
