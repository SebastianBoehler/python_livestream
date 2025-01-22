# Web Page Streaming to X/Twitter

This project captures a webpage using Selenium (headless Chrome) and streams it to X/Twitter via ffmpeg.

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

1. Get your X/Twitter Stream Key:
   - Go to X/Twitter Studio
   - Click "Go Live"
   - Copy your stream key from the stream settings

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
     ```

3. Update `capture_and_stream.py` and update:
   - `STREAM_KEY`: Your X/Twitter stream key
   - `RTMP_URL`: Your X/Twitter RTMP endpoint
   - Optionally adjust:
     - `FPS`: Frames per second (default: 5)
     - `URL_TO_CAPTURE`: The webpage to capture
     - Video quality settings in `FFMPEG_CMD`

## Usage

Run the script:
```bash
# Make sure virtual environment is activated
source venv/bin/activate

# Run the script
python capture_and_stream.py
```

Press Ctrl+C to stop streaming.

## Notes

- The script creates a `frames` directory to store temporary screenshots
- Default resolution is 1920x1080
- Default video bitrate is 2.5 Mbps
- Requires a stable internet connection
- For Mac ARM64 users: Make sure Chrome and ChromeDriver versions match

## Key Features

- Screen capture using Selenium and Chrome in headless mode
- Real-time streaming to X/Twitter
- Local stream testing capability
- Configurable FPS and quality settings

## Prerequisites

- Python 3.x
- Chrome browser
- FFmpeg
- Required Python packages (see `requirements.txt`)

## Installation

1. Clone the repository:
```bash
git clone [repository-url]
cd python_livestream
```

2. Install Python dependencies:
```bash
pip install -r requirements.txt
```

3. Install Chrome and ChromeDriver:
- For Mac: `brew install --cask google-chrome chromedriver`
- For other platforms, download from respective official sources

## Configuration

1. Get your X/Twitter Stream Key:
   - Go to X/Twitter Studio
   - Click "Go Live"
   - Copy your stream key from the stream settings

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
     ```

3. Update the configuration in `capture_and_stream.py`:
```python
STREAM_KEY = "your-stream-key"
URL_TO_CAPTURE = "your-target-url"
FPS = 30  # adjust as needed
```

## Usage

1. Start streaming to X/Twitter:
```bash
python3 capture_and_stream.py
```

2. For local testing (without X/Twitter):
```bash
# Terminal 1 - Start sender with UDP
python3 capture_and_stream.py

# Terminal 2 - Start receiver
python3 receiver.py
```

## Troubleshooting

### Common Issues and Solutions

1. **X/Twitter "No Data" Error**
   - **Issue**: X/Twitter shows "No Data" and "Go Live" button is unclickable
   - **Solution**: Ensure audio stream is included in FFmpeg command
   - Our implementation uses `anullsrc` for null audio source:
     ```python
     "-f", "lavfi",
     "-i", "anullsrc=channel_layout=stereo:sample_rate=44100"
     ```

2. **Stream Quality Issues**
   - Adjust FFmpeg parameters:
     ```python
     "-maxrate", "3000k",
     "-bufsize", "6000k",
     "-preset", "veryfast"
     ```

3. **Chrome/Selenium Issues**
   - Ensure correct Chrome and ChromeDriver versions
   - Check Chrome binary location in code
   - Verify window size settings

## Key Components

1. **capture_and_stream.py**
   - Main streaming script
   - Handles screen capture and FFmpeg streaming

2. **receiver.py**
   - Local testing utility
   - Displays stream in a window
   - Useful for debugging before X/Twitter streaming

## Best Practices

1. **Stream Settings**
   - Use 44.1kHz audio sample rate (X/Twitter standard)
   - Set keyframe interval to 2 * FPS
   - Use "veryfast" preset for good quality/performance balance

2. **Testing**
   - Always test locally first using receiver.py
   - Monitor CPU usage and adjust settings if needed
   - Check X/Twitter Studio's stream health metrics

## Contributing

Feel free to submit issues and pull requests.

## License

[Your chosen license]
