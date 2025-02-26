# Simple YouTube Livestream

A simple Python script to stream a static image with background music to YouTube.

## Requirements

- Python 3.6+
- FFmpeg installed on your system
- YouTube account with live streaming enabled

## Setup

1. Clone this repository:
   ```
   git clone https://github.com/yourusername/python_livestream.git
   cd python_livestream
   ```

2. Install the required Python packages:
   ```
   pip install -r requirements.txt
   ```

3. Create a `.env` file with your YouTube stream key:
   ```
   # YouTube Stream Configuration
   YOUTUBE_STREAM_KEY=your-stream-key-here

   GEMINI_API_KEY=your-gemini-api-key-here
   ```

4. Replace `screenshot.png` with your desired image (1920x1080 resolution recommended)

5. Place your audio file in the `audio` directory as `song.mp3`

## Usage

Run the script:
```
python main.py
```

The script will:
1. Load your YouTube stream key from the `.env` file
2. Stream the static image (`screenshot.png`) with background music (`audio/song.mp3`) to YouTube
3. Continue streaming until you press Ctrl+C to stop

## News Livestreaming with Gemini AI

This project now includes the ability to generate and livestream AI-created news content using Google's Gemini API.

### Setup for Gemini

1. Get a Google Gemini API key from [Google AI Studio](https://ai.google.dev/)

2. Add your Gemini API key to the `.env` file:
   ```
   # Google Gemini Configuration
   GEMINI_API_KEY=your-gemini-api-key-here
   ```

3. Install the additional required packages:
   ```
   pip install google-genai
   ```

### Required Files

- `tts/kokoro/kokoro-v0_19.pth`: The TTS model file (312 MB)
  - Download and place in the tts/kokoro directory
  - TODO: migrate to v1_0

## Troubleshooting

- If FFmpeg is not in your PATH, the script will try to find it at common locations
- Make sure your stream key is correct and your YouTube account has live streaming enabled
- Check that your image and audio files exist and are valid
- If Gemini is not grounding its answer, the script will error

## License

MIT
