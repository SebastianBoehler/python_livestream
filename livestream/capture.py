from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
import time
from .overlay import StreamOverlay

class WebCapture:
    """Handle web page capture using Selenium Chromium WebDriver."""
    
    def __init__(self, url: str, fps: int = 30, overlay_text: str = None, rotating_messages: list = None):
        """
        Initialize web capture.
        
        Args:
            url (str): URL to capture
            fps (int): Frames per second for capture
            overlay_text (str): Text to display in the overlay banner
            rotating_messages (list): List of messages to rotate through
        """
        self.url = url
        self.fps = fps
        self.delay = 1.0 / fps
        self.driver = None
        self.overlay = StreamOverlay(messages=rotating_messages) if (overlay_text or rotating_messages) else None
        self.overlay_text = overlay_text
    
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
    
    def cleanup(self):
        """Clean up resources."""
        if self.driver:
            try:
                self.driver.quit()
            except Exception as e:
                print(f"Error during driver cleanup: {e}")
