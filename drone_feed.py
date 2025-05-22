#!/usr/bin/env python3
"""
Tello Drone Video Feed
Displays the live camera feed in a fixed-size, borderless PIP snapped to the bottom-right.
"""

import time
import cv2
import threading
import numpy as np
from ctypes import windll

# Delay when no frame is received (seconds)
DELAY = 5
# Size of the Picture-in-Picture window
PIP_W, PIP_H = 320, 240   # Width and height in pixels

class TelloCameraDisplay:
    def __init__(self, tello_port=11111):
        """
        Initialize camera display settings.
        tello_port: UDP port where Tello streams video.
        """
        self.tello_port = tello_port
        self.receiving = False   # Flag to control video reception thread
        self.video_thread = None # Thread object for receiving frames
        self.frame = None        # Latest frame from the stream

    def start_receiving(self):
        """
        Launch a background thread to receive video frames over UDP.
        """
        self.receiving = True
        self.video_thread = threading.Thread(
            target=self._receive_video_thread,
            daemon=True
        )
        self.video_thread.start()
        print(f"Receiving Tello video stream on port {self.tello_port}")

    def _receive_video_thread(self):
        """
        Thread target: opens a VideoCapture on the UDP port and
        continually reads frames into self.frame.
        """
        cap = cv2.VideoCapture(f'udp://0.0.0.0:{self.tello_port}')
        while self.receiving:
            ret, frame = cap.read()
            if ret:
                # Store latest successful frame
                self.frame = frame
            else:
                # If no frame, wait briefly before retrying
                time.sleep(0.01)
        cap.release()

    def display_feed(self):
        """
        Create a borderless, always-on-top PIP window and display
        the live video feed until the user quits.
        """
        # Start the reception thread
        self.start_receiving()
        # Allow camera and window to initialize
        time.sleep(2)

        window_name = "Tello Camera Feed"
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(window_name, PIP_W, PIP_H)

        # Draw an initial blank frame so Windows allocates the window
        blank = np.zeros((PIP_H, PIP_W, 3), dtype=np.uint8)
        cv2.imshow(window_name, blank)
        cv2.waitKey(1)
        time.sleep(0.05)

        # Win32 constants for style manipulation
        GWL_STYLE      = -16
        WS_POPUP       = 0x80000000  # Popup style (no borders)
        # Window styles to remove
        WS_CAPTION     = 0x00C00000
        WS_THICKFRAME  = 0x00040000
        WS_MINIMIZEBOX = 0x00020000
        WS_MAXIMIZEBOX = 0x00010000
        WS_SYSMENU     = 0x00080000
        OVERLAPPED     = (WS_CAPTION | WS_THICKFRAME |
                         WS_MINIMIZEBOX | WS_MAXIMIZEBOX | WS_SYSMENU)

        # Window positioning flags
        SWP_NOSIZE     = 0x0001
        SWP_NOACTIVATE = 0x0010
        SWP_SHOWWINDOW = 0x0040
        HWND_TOPMOST   = -1          # Place window above all others

        # Compute bottom-right position with padding
        screen_w = windll.user32.GetSystemMetrics(0)
        screen_h = windll.user32.GetSystemMetrics(1)
        x = screen_w - PIP_W - 10    # 10px margin from right
        y = screen_h - PIP_H         # Align to bottom edge

        # Find the OpenCV window and adjust its style/position
        hwnd = windll.user32.FindWindowW(None, window_name)
        if hwnd:
            # Remove standard window decorations
            current_style = windll.user32.GetWindowLongW(hwnd, GWL_STYLE)
            new_style = (current_style & ~OVERLAPPED) | WS_POPUP
            windll.user32.SetWindowLongW(hwnd, GWL_STYLE, new_style)
            # Move and show the window always on top
            windll.user32.SetWindowPos(
                hwnd, HWND_TOPMOST,
                x, y, 0, 0,
                SWP_NOSIZE | SWP_NOACTIVATE | SWP_SHOWWINDOW
            )
            # Also ensure OpenCV's client area moves correctly
            cv2.moveWindow(window_name, x, y)
        else:
            print(f"⚠️ Could not find window '{window_name}' to strip borders/move")

        # Main display loop: show frames until 'q' or Esc is pressed
        try:
            while True:
                if self.frame is not None:
                    cv2.imshow(window_name, self.frame)
                # Break on 'q' or Esc
                if cv2.waitKey(1) & 0xFF in (27, ord('q')):
                    break
                time.sleep(0.01)
        finally:
            # Clean up on exit
            self.receiving = False
            cv2.destroyWindow(window_name)
            if self.video_thread:
                self.video_thread.join(timeout=1)
            print("Video stream stopped")


def run():
    """
    Entry point: instantiate the display and launch the feed.
    """
    display = TelloCameraDisplay()
    display.display_feed()


if __name__ == "__main__":
    run()
