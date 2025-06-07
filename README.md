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

### Chatterbox TTS

Install [Chatterbox](https://github.com/resemble-ai/chatterbox) for speech synthesis:

```bash
pip install chatterbox-tts torchaudio
```

Run `chatterbox_example.py` to generate a quick demo clip.

The helper module `tts/chatterbox.py` automatically splits long text into
300 character chunks so Chatterbox can synthesize lengthy news scripts.

TTS generation happens in a background thread so the livestream never pauses
while new audio is prepared.


### Hugging Face TTS

Install `huggingface-hub` and use `tts/huggingface.py` to generate speech via the Falcon AI API:

```bash
pip install huggingface-hub
```

The `generate` function mirrors `tts.chatterbox.generate` so you can swap backends easily.
## Continuous News Stream

Set `NEWS_INTERVAL_MINUTES` in your `.env` file to control how often a new news
segment is generated. The `main.py` script keeps streaming `screenshot.png` and
background music at low volume while regularly creating fresh news audio using
Google Gemini and the Chatterbox TTS model. Between segments the background
music keeps the livestream alive so YouTube does not drop the connection.

## Troubleshooting

- If FFmpeg is not in your PATH, the script will try to find it at common locations
- Make sure your stream key is correct and your YouTube account has live streaming enabled
- Check that your image and audio files exist and are valid
- If Gemini is not grounding its answer, the script will error

## License

MIT
