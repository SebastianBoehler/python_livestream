# Goal

Make the HB Capital YouTube playout recover quickly from transient FFmpeg/RTMPS
failures.

# Desired outcome

Chromium and Xvfb remain running while FFmpeg reconnects with a short bounded
backoff. Focused tests verify recovery, shutdown, and redaction before the
change is committed and pushed to `origin/main`.

# Plan

- [x] Extract the FFmpeg subprocess lifecycle into a small module and reconnect
      after unexpected exits with a fixed short bounded backoff.
- [x] Preserve clean SIGINT/SIGTERM shutdown while keeping the browser and
      virtual display alive across reconnects.
- [x] Update the operating documentation to describe in-process reconnects and
      the remaining supervisor responsibility for fatal runtime failures.
- [x] Add focused unit tests for reconnect timing, cancellation, failure
      handling, and secret-safe logging.
- [x] Run focused tests, the full unittest suite, and the required Python
      compile check; review the final diff for scope and file size.
- [x] Commit the approved implementation on `main` with a conventional commit
      message and push it to `origin/main`.
