from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import time
import os
from .overlay import StreamOverlay

class WebCapture:
    """Handle web page capture using Playwright."""
    
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
        self.page = None
        self.browser = None
        self.playwright = None
        self.overlay = StreamOverlay(messages=rotating_messages) if (overlay_text or rotating_messages) else None
        self.overlay_text = overlay_text
        self.audio_file = audio_file
    
    def setup_browser(self):
        """Setup and configure Playwright browser."""
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-gpu',
                '--window-size=1920,1080',
                '--force-device-scale-factor=1',
            ]
        )
        context = self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            device_scale_factor=1,
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
        )
        page = context.new_page()
        page.set_default_timeout(30000)  # Set default timeout to 30 seconds
        return page
    
    def load_page(self, max_retries=3):
        """
        Load the target page with retries.
        
        Args:
            max_retries (int): Maximum number of retry attempts
        
        Returns:
            bool: True if page loaded successfully, False otherwise
        """
        for attempt in range(max_retries):
            try:
                print(f"Loading page (attempt {attempt + 1}/{max_retries})...")
                
                # Navigate to the page with a shorter timeout for initial response
                response = self.page.goto(self.url, wait_until='commit', timeout=20000)
                if not response:
                    print("No response received, retrying...")
                    continue
                    
                if not response.ok:
                    print(f"HTTP {response.status}: {response.status_text}")
                    continue
                
                # Wait for initial render
                self.page.wait_for_load_state('domcontentloaded', timeout=10000)
                
                # Try to wait for network idle, but don't fail if it times out
                try:
                    self.page.wait_for_load_state('networkidle', timeout=5000)
                except PlaywrightTimeoutError:
                    print("Network not idle, but continuing...")
                
                # Hide scrollbars and set overflow
                self.page.evaluate("""
                    () => {
                        document.body.style.overflow = 'hidden';
                        document.documentElement.style.overflow = 'hidden';
                    }
                """)
                
                return True
                
            except PlaywrightTimeoutError:
                print(f"Timeout on attempt {attempt + 1}/{max_retries}")
                if attempt < max_retries - 1:
                    print("Retrying...")
                    time.sleep(1)  # Wait a bit before retrying
                continue
            except Exception as e:
                print(f"Error loading page: {e}")
                if attempt < max_retries - 1:
                    print("Retrying...")
                    time.sleep(1)
                continue
        
        return False
    
    def start_capture(self, streamer):
        """
        Start capturing and streaming.
        
        Args:
            streamer: Streamer object with write_frame method
        """
        print("Launching headless browser...")
        self.page = self.setup_browser()
        
        try:
            # Try to load the page
            if not self.load_page():
                raise Exception("Failed to load page after multiple retries")
            
            # Find the first audio file in the audio directory
            audio_file = None
            audio_dir = '/app/audio'  # Use the container's audio directory path directly
            if os.path.exists(audio_dir):
                audio_files = [f for f in os.listdir(audio_dir) 
                             if f.lower().endswith(('.mp3', '.wav'))]
                if audio_files:
                    audio_file = os.path.join(audio_dir, audio_files[0])
                    print(f"Found audio file: {audio_file}")
                    if not os.path.isfile(audio_file):
                        print(f"Warning: Audio file not found: {audio_file}")
                        audio_file = None
            
            # Set the audio file for the streamer
            if hasattr(streamer, 'audio_file'):
                streamer.audio_file = audio_file
            
            print("Starting stream...")
            last_frame_time = time.time()
            frame_count = 0
            consecutive_errors = 0
            
            while True:
                try:
                    # Capture screenshot
                    screenshot = self.page.screenshot(type='png', timeout=5000)
                    consecutive_errors = 0  # Reset error counter on success
                    
                    # Add overlay if configured
                    if self.overlay:
                        screenshot = self.overlay.add_banner(screenshot, self.overlay_text)
                    
                    # Write frame to streamer
                    streamer.write_frame(screenshot)
                    
                    # Control FPS
                    current_time = time.time()
                    sleep_time = self.delay - (current_time - last_frame_time)
                    if sleep_time > 0:
                        time.sleep(sleep_time)
                    last_frame_time = current_time
                    
                    # Print status every second
                    frame_count += 1
                    if frame_count % self.fps == 0:
                        print(f"Frames captured: {frame_count}", end="\r")
                    
                except PlaywrightTimeoutError:
                    consecutive_errors += 1
                    print(f"\nWarning: Screenshot timed out (error {consecutive_errors}/3)")
                    if consecutive_errors >= 3:
                        print("Too many consecutive errors, reloading page...")
                        if not self.load_page():
                            raise Exception("Failed to reload page after errors")
                        consecutive_errors = 0
                    continue
                    
        except KeyboardInterrupt:
            print("\nStopping capture...")
        except Exception as e:
            print(f"Error during capture: {e}")
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Clean up resources."""
        if self.browser:
            try:
                self.browser.close()
            except Exception as e:
                print(f"Error during browser cleanup: {e}")
        if self.playwright:
            try:
                self.playwright.stop()
            except Exception as e:
                print(f"Error during playwright cleanup: {e}")
