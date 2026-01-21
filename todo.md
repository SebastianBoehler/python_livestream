# TODO

## High Priority

### Faster Screenshot Capture for Livestream

- **Problem**: Playwright screenshot capture is limited to ~10-12 FPS, too slow for realtime 25 FPS streaming
- **Current bottleneck**: `page.screenshot()` takes ~80-100ms per frame
- **Investigate alternatives**:
  - [ ] **Chrome DevTools Protocol (CDP)** - Direct screenshotting via CDP may be faster
  - [ ] **Puppeteer** - May have faster screenshot implementation
  - [ ] **Native screen capture** - Use macOS `screencapture` or `AVFoundation`
  - [ ] **FFmpeg screen capture** - `ffmpeg -f avfoundation -i "1"` for direct screen recording
  - [ ] **Headless browser video export** - Some browsers support video stream output
  - [ ] **Pre-render frames** - For static/semi-static content, cache frames

### Current Stream Settings (Working but slow)

- Resolution: 1280x720
- FPS: 12 (limited by Playwright)
- Video codec: h264_videotoolbox (hardware)
- Video bitrate: 4500k
- Audio: AAC 192k

## Completed

- [x] Parallel capture/encoding with queue-based architecture
- [x] Hardware encoding with VideoToolbox
- [x] Reduced capture resolution to 720p
