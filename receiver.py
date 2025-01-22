import cv2
import numpy as np
import time

def receive_udp_stream(udp_url):
    """
    Receive and display a UDP video stream in a window.
    
    Args:
        udp_url (str): The UDP URL to receive from
    """
    # Open the UDP stream
    print(f"Attempting to connect to stream: {udp_url}")
    cap = cv2.VideoCapture(udp_url)
    
    if not cap.isOpened():
        print("Error: Could not open UDP stream")
        return
    
    print("Successfully connected to stream")
    
    # Create a window
    window_name = "Stream Receiver"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(window_name, 1920, 1080)
    
    try:
        frame_count = 0
        start_time = time.time()
        last_frame_time = start_time
        
        while True:
            # Read a frame from the stream
            ret, frame = cap.read()
            
            if not ret:
                current_time = time.time()
                if current_time - last_frame_time > 5.0:  # No frame for 5 seconds
                    print("\nNo frames received for 5 seconds, reconnecting...")
                    cap.release()
                    cap = cv2.VideoCapture(udp_url)
                    last_frame_time = current_time
                continue
            
            last_frame_time = time.time()
            
            # Display the frame
            cv2.imshow(window_name, frame)
            
            # Calculate and display FPS
            frame_count += 1
            if frame_count % 30 == 0:  # Update FPS every 30 frames
                elapsed_time = time.time() - start_time
                fps = frame_count / elapsed_time
                print(f"FPS: {fps:.2f}", end="\r")
            
            # Break if 'q' is pressed
            if cv2.waitKey(1) & 0xFF == ord('q'):
                print("\nStream closed by user")
                break
                
    except KeyboardInterrupt:
        print("\nStream closed by user (Ctrl+C)")
    finally:
        # Clean up
        cap.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    # Use local UDP URL for testing
    UDP_URL = "udp://127.0.0.1:23000?overrun_nonfatal=1&fifo_size=50000000"
    
    receive_udp_stream(UDP_URL)
