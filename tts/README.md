# Kokoro TTS Integration

This directory contains the Kokoro Text-to-Speech (TTS) integration for the livestream project.

## Setup

1. Ensure you have installed all the required dependencies:
   ```bash
   pip install -r ../requirements.txt
   ```

2. Install espeak-ng, which is required by the phonemizer package:
   ```bash
   # On macOS
   brew install espeak-ng
   
   # On Ubuntu/Debian
   sudo apt-get install espeak-ng
   ```

## Usage

### Basic Usage

```python
from tts.kokoro_wrapper import KokoroTTS

# Initialize the TTS system
tts = KokoroTTS()

# Generate speech with the default voice (bella)
tts.speak("Hello world!", output_file="hello.wav")

# Use a different voice
tts.speak("Hello world!", voice="sarah", output_file="hello_sarah.wav")

# Handle long text with automatic chunking
tts.speak_long_text("This is a very long text...", output_file="long_text.wav")

# Get audio data instead of saving to file
audio_data = tts.speak("Hello world!")
```

### Available Voices

The following voices are available:
- `bella` (default) - Female American
- `sarah` - Female American
- `george` - Male British
- `michael` - Male American
- `neutral` - Neutral voice
- `default` - 50-50 mix of Bella & Sarah

You can list all available voices with:
```python
tts = KokoroTTS()
print(tts.list_available_voices())
```

## Livestream Integration

To use the TTS system with the livestream:

1. Generate TTS audio:
   ```bash
   python tts_livestream.py --text "Hello, this is a test message." --output audio/tts/output.wav
   ```

2. Start a livestream with the generated audio:
   ```bash
   python tts_livestream.py --text "Hello, this is a test message." --stream
   ```

3. You can also read text from a file:
   ```bash
   python tts_livestream.py --text-file my_script.txt --voice sarah --stream
   ```

## Example Script

Check out the `example.py` script for a demonstration of how to use the Kokoro TTS wrapper:

```bash
cd tts
python example.py
```

## Performance Considerations

- The TTS system requires significant CPU resources (or GPU if available).
- For livestreaming, it's recommended to generate the audio in advance rather than in real-time.
- Long texts are automatically chunked to improve processing and memory efficiency.

## Troubleshooting

- If you encounter issues with phonemizer, ensure espeak-ng is installed correctly.
- For CUDA errors, check that your PyTorch installation matches your CUDA version.
- If audio quality is poor, try adjusting the sample rate (default is 24000 Hz).
