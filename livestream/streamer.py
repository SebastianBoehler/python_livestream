import subprocess
import os
import shlex

class YouTubeStreamer:
    """Handle streaming to YouTube using FFmpeg."""
    
    def __init__(self, stream_key: str, video_bitrate: str = '3000k',
                 buffer_size: str = '6000k', fps: int = 30, audio_file: str = None):
        """
        Initialize YouTube streamer.
        
        Args:
            stream_key (str): YouTube stream key
            video_bitrate (str): Maximum video bitrate
            buffer_size (str): FFmpeg buffer size
            fps (int): Frames per second
            audio_file (str): Path to audio file to stream (optional)
        """
        self.stream_key = stream_key
        self.video_bitrate = video_bitrate
        self.buffer_size = buffer_size
        self.fps = fps
        self.process = None
        self.rtmp_url = f"rtmp://a.rtmp.youtube.com/live2/{stream_key}"
        self.audio_file = audio_file
        
    def _create_ffmpeg_command(self):
        """Create FFmpeg command for YouTube streaming."""
        command = [
            "ffmpeg",
            "-y",                 # overwrite output if needed
            "-loglevel", "error",  # Only show errors
            "-thread_queue_size", "1024",  # Increase thread queue size
            # Video input
            "-f", "image2pipe",   # read images from pipe
            "-vcodec", "png",     # input codec is PNG
            "-r", str(self.fps),  # input framerate
            "-i", "-",           # read from stdin
        ]
        
        # Audio input (file or null source)
        if self.audio_file and os.path.exists(self.audio_file):
            print(f"Using audio file: {self.audio_file}")
            # Handle spaces in filename by passing it as a separate argument
            command.extend([
                "-thread_queue_size", "1024",  # Increase thread queue size for audio
                "-stream_loop", "-1",  # Loop the audio infinitely
                "-i", self.audio_file,  # Pass filename as is, subprocess will handle escaping
            ])
        else:
            print("No audio file found, using null audio source")
            command.extend([
                "-f", "lavfi",
                "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
            ])
        
        # Add output options
        command.extend([
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
            # Output options
            "-shortest",  # End when the shortest input ends
            "-f", "flv",
            self.rtmp_url
        ])
        
        return command
    
    def start(self):
        """Start the FFmpeg process."""
        command = self._create_ffmpeg_command()
        print("Starting FFmpeg with command:")
        print(" ".join(f'"{arg}"' if " " in str(arg) else str(arg) for arg in command))
        
        self.process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=10**8
        )
        
        # Start a thread to continuously read stderr
        import threading
        def log_output():
            while self.process and self.process.poll() is None:
                line = self.process.stderr.readline()
                if line and b"error" in line.lower():  # Only show error messages
                    print(f"FFmpeg Error: {line.decode().strip()}")
        
        threading.Thread(target=log_output, daemon=True).start()
    
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
