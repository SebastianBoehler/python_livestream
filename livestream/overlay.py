from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import os
import time

class StreamOverlay:
    """Handle overlay elements for the stream."""
    
    def __init__(self, banner_height: int = 80, font_size: int = 36,
                 bg_color: tuple = (0, 0, 0, 180), text_color: tuple = (255, 255, 255, 255),
                 messages: list = None):
        """
        Initialize stream overlay.
        
        Args:
            banner_height (int): Height of the banner in pixels
            font_size (int): Font size for the banner text
            bg_color (tuple): Background color (R,G,B,A)
            text_color (tuple): Text color (R,G,B,A)
            messages (list): List of messages to rotate through (optional)
        """
        self.banner_height = banner_height
        self.font_size = font_size
        self.bg_color = bg_color
        self.text_color = text_color
        self.last_update = 0
        self.current_index = 0
        self.messages = messages or [
            "Welcome to the Stream!",
            "Don't forget to follow!",
            "Thanks for watching!",
            "Hope you're enjoying the stream!",
            "Feel free to ask questions in chat!"
        ]
        
        # Try to load a system font
        try:
            # Try different system font paths
            font_paths = [
                "/System/Library/Fonts/Helvetica.ttc",  # macOS
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",  # Linux
                "C:\\Windows\\Fonts\\arial.ttf"  # Windows
            ]
            
            for path in font_paths:
                if os.path.exists(path):
                    self.font = ImageFont.truetype(path, self.font_size)
                    break
            else:
                # Fallback to default font
                self.font = ImageFont.load_default()
        except Exception as e:
            print(f"Warning: Could not load system font: {e}")
            self.font = ImageFont.load_default()
    
    def get_current_text(self, text: str = None) -> str:
        """
        Get the current banner text based on time and rotation.
        
        Args:
            text (str): Optional override text
            
        Returns:
            str: Current banner text
        """
        if text:
            return text
            
        current_time = time.time()
        # Check if 3 minutes (180 seconds) have passed
        if current_time - self.last_update >= 180:
            self.current_index = (self.current_index + 1) % len(self.messages)
            self.last_update = current_time
            
        return self.messages[self.current_index]
    
    def add_banner(self, image_data: bytes, text: str = None) -> bytes:
        """
        Add a banner overlay to the image.
        
        Args:
            image_data (bytes): Original image data in PNG format
            text (str): Optional text override for the banner
        
        Returns:
            bytes: Modified image data in PNG format
        """
        # Get the current dynamic text
        display_text = self.get_current_text(text)
        
        # Open the image from bytes
        image = Image.open(BytesIO(image_data))
        
        # Create a new image with an alpha channel
        overlay = Image.new('RGBA', image.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        
        # Calculate banner position (at the bottom)
        banner_box = [
            0,  # left
            image.height - self.banner_height,  # top
            image.width,  # right
            image.height  # bottom
        ]
        
        # Draw semi-transparent banner background
        draw.rectangle(banner_box, fill=self.bg_color)
        
        # Calculate text position
        text_bbox = draw.textbbox((0, 0), display_text, font=self.font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
        
        text_position = (
            (image.width - text_width) // 2,  # center horizontally
            image.height - (self.banner_height + text_height) // 2  # center vertically in banner
        )
        
        # Draw text
        draw.text(text_position, display_text, font=self.font, fill=self.text_color)
        
        # Composite the overlay onto the original image
        result = Image.alpha_composite(image.convert('RGBA'), overlay)
        
        # Convert back to PNG bytes
        output = BytesIO()
        result.save(output, format='PNG')
        return output.getvalue()
