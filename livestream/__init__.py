"""
YouTube Live Streaming Package

This package provides functionality for capturing web content and streaming it to YouTube Live.
"""

from .capture import WebCapture
from .streamer import YouTubeStreamer

__all__ = ['WebCapture', 'YouTubeStreamer']
