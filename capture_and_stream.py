import os
import time
import subprocess
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# -----------------------------------------------
# CONFIGURATION
# -----------------------------------------------
URL_TO_CAPTURE = os.getenv('URL_TO_CAPTURE')
FRAMES_DIR = "frames"
FPS = int(os.getenv('FPS', '30'))
VIDEO_BITRATE = os.getenv('VIDEO_BITRATE', '3000k')
BUFFER_SIZE = os.getenv('BUFFER_SIZE', '6000k')

# YouTube RTMP URL
STREAM_KEY = os.getenv('YOUTUBE_STREAM_KEY')
if not STREAM_KEY:
    raise ValueError("YouTube stream key not found in environment variables")
RTMP_URL = f"rtmp://a.rtmp.youtube.com/live2/{STREAM_KEY}"

# FFmpeg command for YouTube streaming with null audio
FFMPEG_CMD = [
    "ffmpeg",
    "-y",                 # overwrite output if needed
    # Video input
    "-f", "image2pipe",   # read images from pipe
    "-vcodec", "png",     # input codec is PNG
    "-r", str(FPS),       # input framerate
    "-i", "-",           # read from stdin
    # Null audio input
    "-f", "lavfi",
    "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
    # Video encoding
    "-c:v", "libx264",
    "-preset", "veryfast",
    "-maxrate", VIDEO_BITRATE,
    "-bufsize", BUFFER_SIZE,
    "-pix_fmt", "yuv420p",
    "-g", "50",
    # Audio encoding
    "-c:a", "aac",
    "-b:a", "128k",
    "-ar", "44100",
    # Output
    "-f", "flv",
    RTMP_URL
]

def setup_chrome_driver():
    """Setup and return configured Chrome WebDriver."""
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")  # Updated headless mode syntax
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")  # Updated to standard 1080p resolution
    chrome_options.add_argument("--force-device-scale-factor=1")
    chrome_options.add_argument("--hide-scrollbars")
    
    # Set Chrome binary location for Mac
    chrome_options.binary_location = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    
    # Use system-installed ChromeDriver
    service = Service('/opt/homebrew/bin/chromedriver')
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    # Set viewport size explicitly
    driver.execute_cdp_cmd('Emulation.setDeviceMetricsOverride', {
        'mobile': False,
        'width': 1920,
        'height': 1080,
        'deviceScaleFactor': 1,
    })
    
    return driver

def clean_frames_directory():
    """Ensure frames directory exists."""
    if not os.path.exists(FRAMES_DIR):
        os.makedirs(FRAMES_DIR)

def main():
    # 1) Start ffmpeg in background with pipe
    print("Starting ffmpeg streaming...")
    ffmpeg_process = subprocess.Popen(
        FFMPEG_CMD,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=10**8  # Set a larger buffer
    )

    # 2) Set up headless Chrome with Selenium
    print("Launching headless Chrome...")
    driver = setup_chrome_driver()
    
    try:
        driver.get(URL_TO_CAPTURE)
        print("Waiting for page to load...")
        time.sleep(5)  # Give the page time to load
        
        # Set viewport size again after page load to ensure it takes effect
        driver.execute_cdp_cmd('Emulation.setDeviceMetricsOverride', {
            'mobile': False,
            'width': 1920,
            'height': 1080,
            'deviceScaleFactor': 1,
        })
        
        # Force a specific document size
        driver.execute_script("""
            document.body.style.overflow = 'hidden';
            document.documentElement.style.overflow = 'hidden';
        """)
        
        # 3) Continuously capture and stream screenshots
        print(f"Starting to capture and stream at {FPS} FPS.")
        delay = 1.0 / FPS
        frame_count = 0
        
        while True:
            # Check if FFmpeg is still running
            if ffmpeg_process.poll() is not None:
                error = ffmpeg_process.stderr.read().decode()
                print(f"FFmpeg process terminated unexpectedly. Error: {error}")
                break

            try:
                # Capture screenshot as PNG bytes
                png_bytes = driver.get_screenshot_as_png()
                # Write directly to FFmpeg's stdin
                ffmpeg_process.stdin.write(png_bytes)
                ffmpeg_process.stdin.flush()  # Ensure the data is sent
                
                frame_count += 1
                if frame_count % 30 == 0:  # Print status every second
                    print(f"Frames sent: {frame_count}", end="\r")
                
                time.sleep(delay)
            except BrokenPipeError:
                print("FFmpeg pipe broken. Checking FFmpeg error output:")
                error = ffmpeg_process.stderr.read().decode()
                print(f"FFmpeg error: {error}")
                break
            except Exception as e:
                print(f"Error in streaming loop: {str(e)}")
                break

    except KeyboardInterrupt:
        print("\nStopping capture (Ctrl+C detected)...")
    except Exception as e:
        print(f"Error occurred: {str(e)}")
    finally:
        # 4) Cleanup
        print("Cleaning up...")
        try:
            if ffmpeg_process.stdin:
                ffmpeg_process.stdin.close()
            if ffmpeg_process.stderr:
                error = ffmpeg_process.stderr.read().decode()
                if error:
                    print(f"FFmpeg final error output: {error}")
            driver.quit()
            ffmpeg_process.terminate()
            ffmpeg_process.wait(timeout=5)
        except Exception as cleanup_error:
            print(f"Error during cleanup: {cleanup_error}")
        print("Streaming ended. Exiting.")

if __name__ == "__main__":
    main()
