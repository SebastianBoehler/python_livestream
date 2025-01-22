# Web Page Streaming to RTMP

This project captures a webpage using Selenium (headless Chrome) and streams it to any RTMP endpoint (X/Twitter, YouTube, Twitch, custom RTMP servers, etc.) via ffmpeg.

## Requirements

- Python 3.7+
- Chrome/Chromium browser
- ffmpeg
- Virtual environment (recommended)

## Installation

### 1. Set up Virtual Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Update pip
pip install --upgrade pip
```

### 2. Install Python Dependencies
```bash
pip install -r requirements.txt
```

### 3. Install System Dependencies

#### On macOS:
```bash
# Install ffmpeg
brew install ffmpeg

# For M1/M2/M3 Macs (ARM64):
# Make sure Chrome is installed
brew install --cask google-chrome

# Install ChromeDriver
brew install --cask chromedriver
```

#### On Ubuntu/Debian:
```bash
# Install ffmpeg and Chrome
sudo apt-get update
sudo apt-get install -y ffmpeg
sudo apt-get install -y google-chrome-stable

# Install ChromeDriver (match version with your Chrome)
# Check your Chrome version first:
google-chrome --version
# Then download matching ChromeDriver from:
# https://chromedriver.chromium.org/downloads
```

### 4. Troubleshooting Chrome/ChromeDriver

If you encounter issues with ChromeDriver on Mac ARM64:

1. Verify Chrome installation:
```bash
# Chrome should be in Applications folder
ls /Applications/Google\ Chrome.app
```

2. Verify ChromeDriver:
```bash
# Check ChromeDriver version
chromedriver --version

# Make sure it matches your Chrome version
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --version
```

3. Common fixes:
- If ChromeDriver gives permission errors:
  ```bash
  xattr -d com.apple.quarantine $(which chromedriver)
  ```
- If Chrome isn't found:
  ```bash
  # Add to your script:
  chrome_options.binary_location = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
  ```

## Configuration

1. Get your RTMP stream key from your streaming platform (X/Twitter, YouTube, Twitch, etc.)

2. Set up environment variables:
   - Copy `.env.example` to `.env`:
     ```bash
     cp .env.example .env
     ```
   - Edit `.env` with your settings:
     ```env
     STREAM_KEY=your-stream-key-here
     URL_TO_CAPTURE=https://www.example.com
     FPS=30
     VIDEO_BITRATE=3000k
     BUFFER_SIZE=6000k
     RTMP_URL=rtmp://your-rtmp-server-url
     ```

## Usage

Run the script:
```bash
# Make sure virtual environment is activated
source venv/bin/activate

# Run the script
python capture_and_stream.py
```

Press Ctrl+C to stop streaming.

## Technical Details

- Creates a `frames` directory for temporary screenshots
- Default resolution: 1920x1080
- Default video bitrate: 2.5 Mbps
- Configurable FPS and quality settings
- Uses headless Chrome for web capture
- Includes null audio source for platforms requiring audio

## Troubleshooting

### X/Twitter "No Data" Error
- **Issue**: X/Twitter shows "No Data" and "Go Live" button is unclickable
- **Solution**: Ensure audio stream is included in FFmpeg command
- Our implementation uses `anullsrc` for null audio source
```python
"-f", "lavfi",
"-i", "anullsrc=channel_layout=stereo:sample_rate=44100"
```

## Contributing

Feel free to submit issues and pull requests.

## License

[Your chosen license]
