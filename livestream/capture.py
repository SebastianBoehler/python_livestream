from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
import time
import os
from .overlay import StreamOverlay

class WebCapture:
    """Handle web page capture using Selenium Chromium WebDriver."""
    
    def __init__(self, url: str, fps: int = 30, overlay_text: str = None, rotating_messages: list = None,
                 audio_file: str = None):
        """
        Initialize web capture.
        
        Args:
            url (str): URL to capture
            fps (int): Frames per second for capture
            overlay_text (str): Text to display in the overlay banner
            rotating_messages (list): List of messages to rotate through
            audio_file (str): Optional specific audio file to play
        """
        self.url = url
        self.fps = fps
        self.delay = 1.0 / fps
        self.driver = None
        self.overlay = StreamOverlay(messages=rotating_messages) if (overlay_text or rotating_messages) else None
        self.overlay_text = overlay_text
        self.audio_file = audio_file
    
    def setup_chrome_driver(self):
        """Setup and configure Chromium WebDriver."""
        chrome_options = Options()
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--force-device-scale-factor=1")
        chrome_options.add_argument("--hide-scrollbars")
        
        # Use system-installed Chromium
        chrome_options.binary_location = "/usr/bin/chromium"
        
        # Use system-installed chromedriver
        service = Service('/usr/bin/chromedriver')
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # Set viewport size explicitly
        driver.execute_cdp_cmd('Emulation.setDeviceMetricsOverride', {
            'mobile': False,
            'width': 1920,
            'height': 1080,
            'deviceScaleFactor': 1,
        })
        
        return driver
    
    def start_capture(self, streamer):
        """
        Start capturing and streaming.
        
        Args:
            streamer: Streamer object with write_frame method
        """
        print("Launching headless Chromium...")
        self.driver = self.setup_chrome_driver()
        
        try:
            self.driver.get(self.url)
            print("Waiting for page to load...")
            time.sleep(5)  # Give the page time to load
            
            # Set viewport size again after page load
            self.driver.execute_cdp_cmd('Emulation.setDeviceMetricsOverride', {
                'mobile': False,
                'width': 1920,
                'height': 1080,
                'deviceScaleFactor': 1,
            })
            
            # Force a specific document size
            self.driver.execute_script("""
                document.body.style.overflow = 'hidden';
                document.documentElement.style.overflow = 'hidden';
            """)
            
            # Find the first audio file in the audio directory
            audio_file = None
            audio_dir = '/app/audio'  # Use the container's audio directory path directly
            if os.path.exists(audio_dir):
                audio_files = [f for f in os.listdir(audio_dir) 
                             if f.lower().endswith(('.mp3', '.wav'))]
                if audio_files:
                    # Use os.path.join for proper path handling
                    audio_file = os.path.join(audio_dir, audio_files[0])
                    print(f"Found audio file: {audio_file}")
                    # Verify file exists and is readable
                    if not os.path.isfile(audio_file):
                        print(f"Warning: Audio file not found: {audio_file}")
                        audio_file = None
                    elif not os.access(audio_file, os.R_OK):
                        print(f"Warning: Audio file not readable: {audio_file}")
                        audio_file = None
                    else:
                        # Double-check the file exists
                        print(f"Verifying audio file exists: {os.path.exists(audio_file)}")
                        print(f"File permissions: {oct(os.stat(audio_file).st_mode)[-3:]}")
                else:
                    print("No audio files found in audio directory")
            else:
                print(f"Audio directory not found at: {audio_dir}")
            
            # Set the audio file for the streamer
            if hasattr(streamer, 'audio_file'):
                streamer.audio_file = audio_file
            
            print(f"Starting to capture at {self.fps} FPS.")
            frame_count = 0
            
            while True:
                # Capture screenshot as PNG bytes
                png_bytes = self.driver.get_screenshot_as_png()
                
                # Add overlay if configured
                if self.overlay:
                    png_bytes = self.overlay.add_banner(png_bytes, self.overlay_text)
                
                streamer.write_frame(png_bytes)
                
                frame_count += 1
                if frame_count % self.fps == 0:  # Print status every second
                    print(f"Frames sent: {frame_count}", end="\r")
                
                time.sleep(self.delay)
                
        except Exception as e:
            print(f"Error in capture: {str(e)}")
            raise
        finally:
            if self.driver:
                self.driver.quit()
    
    def cleanup(self):
        """Clean up resources."""
        if self.driver:
            try:
                self.driver.quit()
            except Exception as e:
                print(f"Error during driver cleanup: {e}")
