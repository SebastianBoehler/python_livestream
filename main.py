import os
from dotenv import load_dotenv
from livestream.capture import WebCapture
from livestream.streamer import YouTubeStreamer

def main():
    # Load environment variables
    load_dotenv()
    
    # Validate required environment variables
    required_vars = ['YOUTUBE_STREAM_KEY', 'URL_TO_CAPTURE']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
    
    # Define rotating messages
    rotating_messages = [
        "HB Capital Market Overview Stream",
        "⚠️ DISCLAIMER: This content is for informational purposes only. Not financial advice.",
        "Market analysis and commentary provided by HB Capital",
        "⚠️ Past performance is not indicative of future results",
        "Subscribe for daily market insights"
    ]
    
    try:
        # Initialize web capture with overlay
        capture = WebCapture(
            url=os.getenv('URL_TO_CAPTURE'),
            fps=int(os.getenv('FPS', '30')),
            overlay_text=os.getenv('OVERLAY_TEXT'),  # Can be None, will use rotating messages
            rotating_messages=rotating_messages
        )
        
        # Initialize YouTube streamer
        streamer = YouTubeStreamer(
            stream_key=os.getenv('YOUTUBE_STREAM_KEY'),
            video_bitrate=os.getenv('VIDEO_BITRATE', '3000k'),
            buffer_size=os.getenv('BUFFER_SIZE', '6000k'),
            fps=int(os.getenv('FPS', '30'))
        )
        
        # Start streaming
        print("Starting capture and stream...")
        capture.start_capture(streamer)
        
    except KeyboardInterrupt:
        print("\nStopping stream (Ctrl+C detected)...")
    except Exception as e:
        print(f"Error occurred: {str(e)}")
    finally:
        # Cleanup
        if 'capture' in locals():
            capture.cleanup()
        if 'streamer' in locals():
            streamer.cleanup()
        print("Streaming ended. Exiting.")

if __name__ == "__main__":
    main()
