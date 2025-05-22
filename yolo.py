#!/usr/bin/env python3
"""
YOLO Drone Vision Module
Processes live camera frames with a YOLO model, annotates detections,
and shares drone position via UDP logic.
"""

import cv2             # OpenCV for image capture and display
import udp_logic       # Custom module for UDP-based drone communication
from ultralytics import YOLO  # Ultralytics YOLO model API

# Configuration constants
WEIGHTS       = "YOLOv11/runs/detect/train41/weights/best.pt"  # Path to trained model weights
CAM_IDX       = 1              # Camera index for cv2.VideoCapture
PROC_W, PROC_H = 1920, 1080    # Resolution for processing frames
OUT_W, OUT_H   = 1920, 1080    # Resolution for output/display scaling
CONF_THR      = 0.3            # Confidence threshold for detections
DEBUG         = False          # Verbose model output flag

# Stores the last known drone position (x, y)
last_location = None

def initialize_model():
    """
    Load and return the YOLO model with specified weights.
    """
    print("[VISION] Loading YOLO model...")
    return YOLO(WEIGHTS)


def initialize_camera():
    """
    Open the video capture device and set its resolution.
    """
    cap = cv2.VideoCapture(CAM_IDX)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, PROC_W)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, PROC_H)
    return cap


def setup_display():
    """
    Create a fullscreen OpenCV window for inference display.
    """
    cv2.namedWindow("YOLO Inference", cv2.WINDOW_NORMAL)
    cv2.setWindowProperty(
        "YOLO Inference",
        cv2.WND_PROP_FULLSCREEN,
        cv2.WINDOW_FULLSCREEN
    )


def calculate_scale_factors():
    """
    Compute scaling factors from processing resolution to output resolution.
    Returns (scale_x, scale_y).
    """
    scale_x = OUT_W / PROC_W
    scale_y = OUT_H / PROC_H
    return scale_x, scale_y


def process_frame(frame, model, scale_x, scale_y):
    """
    Apply the YOLO model to a frame, annotate detections,
    update drone position via udp_logic, and return annotated image.
    """
    global last_location

    # Mirror the frame horizontally for intuitive user view
    frame = cv2.flip(frame, 1)
    # Run inference (with optional verbose output)
    results = model(frame, verbose=DEBUG)
    boxes = results[0].boxes  # Detected bounding boxes
    annotated = frame.copy()  # Copy frame for drawing
    new_location = None       # To capture the first valid detection

    # Iterate detections to find the drone (class ID 0)
    for box in boxes:
        cls_id = int(box.cls[0])             # Class of detection
        conf = float(box.conf[0])            # Confidence score
        if cls_id == 0 and conf >= CONF_THR:
            # Extract bounding box coordinates
            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy().astype(int)
            # Draw rectangle around the drone
            cv2.rectangle(
                annotated, (x1, y1), (x2, y2),
                (0, 255, 0), 2
            )
            # Compute center point and scale to output coordinates
            cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
            sx = int(cx * scale_x)
            sy = OUT_H - int(cy * scale_y)
            # Annotate coordinates on the frame
            label = f"({sx},{sy})"
            cv2.putText(
                annotated, label,
                (x1, y1 - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.9, (0, 255, 0), 2
            )
            new_location = (sx, sy)
            break  # Only consider the first valid detection

    # Update UDP logic with new or last known location
    if new_location:
        udp_logic.drone_location = new_location
        last_location = new_location
    elif last_location:
        udp_logic.drone_location = last_location

    return annotated


def main_loop(cap, model, scale_x, scale_y):
    """
    Capture frames in a loop, process and display them,
    exit on 'q' key press.
    """
    while cap.isOpened():
        success, frame = cap.read()
        if not success:
            print("[VISION] Frame grab failed, exiting.")
            break

        annotated = process_frame(frame, model, scale_x, scale_y)
        cv2.imshow("YOLO Inference", annotated)

        # Exit loop if 'q' is pressed
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break


def run():
    """
    Entry point: initialize model, camera, display settings,
    then start the main processing loop.
    """
    model = initialize_model()
    cap = initialize_camera()
    setup_display()
    scale_x, scale_y = calculate_scale_factors()

    main_loop(cap, model, scale_x, scale_y)

    # Cleanup resources
    cap.release()
    cv2.destroyAllWindows()
    print("[VISION] Thread ending.")


if __name__ == "__main__":
    run()
