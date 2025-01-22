import subprocess

class YouTubeStreamer:
    """Handle streaming to YouTube using FFmpeg."""
    
    def __init__(self, stream_key: str, video_bitrate: str = '3000k',
                 buffer_size: str = '6000k', fps: int = 30):
        """
        Initialize YouTube streamer.
        
        Args:
            stream_key (str): YouTube stream key
            video_bitrate (str): Maximum video bitrate
            buffer_size (str): FFmpeg buffer size
            fps (int): Frames per second
        """
        self.stream_key = stream_key
        self.video_bitrate = video_bitrate
        self.buffer_size = buffer_size
        self.fps = fps
        self.process = None
        self.rtmp_url = f"rtmp://a.rtmp.youtube.com/live2/{stream_key}"
        
    def _create_ffmpeg_command(self):
        """Create FFmpeg command for YouTube streaming."""
        return [
            "ffmpeg",
            "-y",                 # overwrite output if needed
            # Video input
            "-f", "image2pipe",   # read images from pipe
            "-vcodec", "png",     # input codec is PNG
            "-r", str(self.fps),  # input framerate
            "-i", "-",           # read from stdin
            # Null audio input
            "-f", "lavfi",
            "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
            # Video encoding
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-maxrate", self.video_bitrate,
            "-bufsize", self.buffer_size,
            "-pix_fmt", "yuv420p",
            "-g", "50",
            # Audio encoding
            "-c:a", "aac",
            "-b:a", "128k",
            "-ar", "44100",
            # Output
            "-f", "flv",
            self.rtmp_url
        ]
    
    def start(self):
        """Start the FFmpeg process."""
        print("Starting FFmpeg streaming...")
        command = self._create_ffmpeg_command()
        self.process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=10**8
        )
    
    def write_frame(self, frame_data: bytes):
        """
        Write a frame to the stream.
        
        Args:
            frame_data (bytes): Frame data in PNG format
        """
        if not self.process:
            self.start()
        
        try:
            self.process.stdin.write(frame_data)
            self.process.stdin.flush()
        except BrokenPipeError:
            error = self.process.stderr.read().decode()
            print(f"FFmpeg error: {error}")
            raise
        
        # Check if FFmpeg is still running
        if self.process.poll() is not None:
            error = self.process.stderr.read().decode()
            raise RuntimeError(f"FFmpeg process terminated unexpectedly. Error: {error}")
    
    def cleanup(self):
        """Clean up FFmpeg process."""
        if self.process:
            try:
                if self.process.stdin:
                    self.process.stdin.close()
                if self.process.stderr:
                    error = self.process.stderr.read().decode()
                    if error:
                        print(f"FFmpeg final error output: {error}")
                self.process.terminate()
                self.process.wait(timeout=5)
            except Exception as e:
                print(f"Error during FFmpeg cleanup: {e}")
