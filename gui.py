import tkinter as tk
from tkinter import Button

# Virtual canvas dimensions (logical units)
VIRTUAL_WIDTH, VIRTUAL_HEIGHT = 1920, 1080

# Grid settings
GRID_SIZE = 50              # Distance between grid lines
GRID_COLOR = "gray"         # Color of grid lines

# Route drawing settings
ROUTE_COLOR_VERT = "green"   # Color for vertical segments of the route
ROUTE_COLOR_HORIZ = "blue"   # Color for horizontal segments of the route
ROUTE_DASH = (2, 2)           # Dash pattern for horizontal lines
LINE_WIDTH = 25               # Thickness of route lines

# Waypoint marker settings
WAYPOINT_COLOR = "red"       # Color of waypoint circles
WAYPOINT_RADIUS = 35          # Radius of waypoint markers
TEXT_COLOR = "black"         # Color of waypoint label text
TEXT_FONT = ("Arial", 15, "bold")  # Font for waypoint labels

# Constraints for adding waypoints
MIN_DELTA_X = 256             # Minimum horizontal distance between successive waypoints
MIN_DELTA_Y = 144             # Minimum vertical distance between successive waypoints
MIN_ALLOWED_AXIS_DELTA = 5    # Minimum movement along an axis to count as intentional
MIN_EDGE_MARGIN = 150         # Margin from the edges where clicks are ignored

# State variables
waypoints = []        # Recorded logical coordinates of waypoints
recording = False     # Flag: are we currently recording clicks?
destination_list = [] # Final list of waypoints for the drone

# GUI objects (initialized later)
root = tk.Tk()
canvas = None
rec_btn = None
scale_x = 1.0
scale_y = 1.0

def draw_grid():
    """
    Draws a grid over the canvas to match the virtual coordinate space.
    """
    canvas.delete("grid")
    # Draw vertical lines
    for x in range(0, VIRTUAL_WIDTH, GRID_SIZE):
        sx = x * scale_x
        canvas.create_line(sx, 0, sx, VIRTUAL_HEIGHT * scale_y,
                           fill=GRID_COLOR, tags="grid")
    # Draw horizontal lines
    for y in range(0, VIRTUAL_HEIGHT, GRID_SIZE):
        sy = y * scale_y
        canvas.create_line(0, sy, VIRTUAL_WIDTH * scale_x, sy,
                           fill=GRID_COLOR, tags="grid")

def draw_waypoints():
    """
    Draws the recorded waypoints and connecting route on the canvas.
    """
    canvas.delete("route")

    # Draw connecting lines between waypoints
    for i in range(1, len(waypoints)):
        x0, y0 = waypoints[i - 1]
        x1, y1 = waypoints[i]

        # Convert logical coords to screen coords (invert Y axis)
        draw_x0 = x0 * scale_x
        draw_y0 = (VIRTUAL_HEIGHT - y0) * scale_y
        draw_x1 = x1 * scale_x
        draw_y1 = (VIRTUAL_HEIGHT - y1) * scale_y

        # Vertical segment: solid green
        canvas.create_line(draw_x0, draw_y0, draw_x0, draw_y1,
                           fill=ROUTE_COLOR_VERT, width=LINE_WIDTH,
                           tags="route")
        # Horizontal segment: dashed blue
        canvas.create_line(draw_x0, draw_y1, draw_x1, draw_y1,
                           fill=ROUTE_COLOR_HORIZ, dash=ROUTE_DASH,
                           width=LINE_WIDTH, tags="route")

    # Draw waypoint markers and labels
    for i, (x, y) in enumerate(waypoints):
        draw_x = x * scale_x
        draw_y = (VIRTUAL_HEIGHT - y) * scale_y

        # Circle for the waypoint
        canvas.create_oval(
            draw_x - WAYPOINT_RADIUS, draw_y - WAYPOINT_RADIUS,
            draw_x + WAYPOINT_RADIUS, draw_y + WAYPOINT_RADIUS,
            fill=WAYPOINT_COLOR, tags="route"
        )
        # Number label inside the circle
        canvas.create_text(
            draw_x, draw_y,
            text=str(i + 1), fill=TEXT_COLOR,
            font=TEXT_FONT, tags="route"
        )

def on_click(event):
    """
    Handler for mouse clicks: records waypoints when in recording mode,
    enforcing margin and distance constraints.
    """
    if not recording:
        return

    # Convert screen coords back to logical coords
    x = event.x / scale_x
    y = VIRTUAL_HEIGHT - (event.y / scale_y)

    # Ignore clicks too close to edges
    if (x < MIN_EDGE_MARGIN or x > VIRTUAL_WIDTH - MIN_EDGE_MARGIN or
        y < MIN_EDGE_MARGIN or y > VIRTUAL_HEIGHT - MIN_EDGE_MARGIN):
        return

    # If this is the first waypoint, just add it
    if not waypoints:
        waypoints.append((x, y))
        draw_waypoints()
        return

    last_x, last_y = waypoints[-1]
    dx = abs(x - last_x)
    dy = abs(y - last_y)

    # Enforce minimum movement in at least one axis while the other axis stays small
    if (dx < MIN_DELTA_X and dx >= MIN_ALLOWED_AXIS_DELTA and dy >= MIN_DELTA_Y) or \
       (dy < MIN_DELTA_Y and dy >= MIN_ALLOWED_AXIS_DELTA and dx >= MIN_DELTA_X):
        pass
    # If movement is too small overall, ignore click
    elif dx < MIN_DELTA_X and dy < MIN_DELTA_Y:
        return

    # Record the valid waypoint and redraw
    waypoints.append((x, y))
    draw_waypoints()

def toggle_rec():
    """
    Toggles recording mode on and off. Clears waypoints if turning off.
    """
    global recording, waypoints, destination_list
    if not recording:
        recording = True
        rec_btn.config(text="CLEAR")
    else:
        recording = False
        rec_btn.config(text="REC")
        # Reset recorded data
        waypoints.clear()
        destination_list.clear()
        canvas.delete("route")

def start_drone():
    """
    Called when START button is pressed: copies recorded waypoints
    to destination_list for the drone to follow.
    """
    global destination_list
    destination_list.clear()
    destination_list.extend(waypoints)
    print("Start pressed - saved waypoints to destination_list:", destination_list)

def stop_drone():
    """
    Called when STOP button is pressed: exits the application.
    """
    print("Stop pressed")
    import sys
    sys.exit(0)

def configure_root_window(screen_width, screen_height):
    """
    Set up the main window properties: size, transparency,
    always-on-top, and borderless.
    """
    root.title("Drone Overlay")
    root.geometry(f"{screen_width}x{screen_height}+0+0")
    root.configure(bg='white')
    root.wm_attributes('-alpha', 0.5)       # Semi-transparent
    root.wm_attributes('-topmost', True)    # Stay on top of other windows
    root.overrideredirect(True)            # Remove window borders

def create_canvas(screen_width, screen_height):
    """
    Create and pack the canvas widget for drawing.
    """
    global canvas
    canvas_frame = tk.Frame(root)
    canvas_frame.pack(fill="both", expand=True)

    canvas = tk.Canvas(
        canvas_frame,
        width=screen_width,
        height=screen_height - 60,
        bg='white', highlightthickness=0
    )
    canvas.pack(fill="both", expand=True)

def create_buttons():
    """
    Create and pack the REC, START, and STOP buttons.
    """
    global rec_btn
    btn_frame = tk.Frame(root, bg='white')
    btn_frame.pack(fill='x', side='bottom')

    rec_btn = Button(btn_frame, text="REC", width=10, command=toggle_rec)
    rec_btn.pack(side='left', padx=5, pady=5)

    Button(btn_frame, text="START", width=10, command=start_drone).pack(side='left', padx=5)
    Button(btn_frame, text="STOP", width=10, command=root.destroy).pack(side='left', padx=5)

def initialize_screen_scaling():
    """
    Calculate and store scaling factors between logical and screen coords.
    """
    global scale_x, scale_y
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    scale_x = screen_width / VIRTUAL_WIDTH
    scale_y = screen_height / VIRTUAL_HEIGHT
    return screen_width, screen_height

def initialize_gui():
    """
    Set up the full GUI: scaling, window config, canvas, buttons,
    event bindings, and initial grid draw.
    """
    screen_width, screen_height = initialize_screen_scaling()
    configure_root_window(screen_width, screen_height)
    create_canvas(screen_width, screen_height)
    create_buttons()
    canvas.bind("<Button-1>", on_click)
    draw_grid()

def run():
    """
    Entry point: initialize GUI and start the Tk event loop.
    """
    initialize_gui()
    root.mainloop()

if __name__ == "__main__":
    run()