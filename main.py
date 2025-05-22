# main.py

import threading, gui, udp_logic, yolo, drone_ap_connect, drone_feed

def drone_cam_feed():
    drone_feed.run() # Start the drone camera feed when 

def ai_vision_tracking():
    yolo.run() # Start the AI vision tracking

def udp_command_loop():
    drone_ap_connect.run() # Connect to drone AP before running the mission
    udp_logic.run() # Start UDP logic

if __name__ == "__main__":

    threading.Thread(target=ai_vision_tracking, daemon=True).start() # Start the AI vision tracking

    threading.Thread(target=udp_command_loop, daemon=True).start() # Start the UDP command loop

    gui.run() # Tkinter needs to run in main thread to function properly because of its event loop