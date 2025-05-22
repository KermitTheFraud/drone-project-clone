import navigation as NAV, udp_sender as UDP, time, gui, threading  # import modules for nav logic, UDP comms, timing, and GUI
from drone_feed import run as drone_feed_run  # import camera feed module

drone_location = None  # global updated by vision thread with current (x, y) position

DELAY = 0.1  # seconds to wait between successive UDP commands

'''Check if current position is within given tolerances of target.'''
def is_close_enough(current, target, x_tol=100, y_tol=50):
    """
    Args:
        current (tuple): Current (x, y) position
        target (tuple): Desired (x, y) position
        x_tol (int): Maximum horizontal tolerance
        y_tol (int): Maximum vertical tolerance
    Returns:
        bool: True if position within tolerances, else False
    """
    if current is None or target is None:
        return False  # missing either current or target data

    dx = abs(current[0] - target[0])  # horizontal distance
    dy = abs(current[1] - target[1])  # vertical distance

    return dx <= x_tol and dy <= y_tol  # within both tolerances

'''Send a Tello UDP command if its value exceeds thresholds.'''
def send_command_if_needed(cmd, skip_threshold=5, min_value=20):
    """
    Args:
        cmd (str): Command string in format '<direction> <value>'
        skip_threshold (int): Values <= this are ignored
        min_value (int): Smallest value to send if above skip_threshold
    """
    direction, value_str = cmd.split()  # split into action and amount
    value = int(value_str)  # convert amount to integer

    if value <= skip_threshold:
        print(f"Skipping small movement: {cmd}")  # ignore negligible adjustments
        return

    if value < min_value:
        value = min_value  # enforce minimum movement
    cmd_to_send = f"{direction} {value}"  # reconstruct command

    print(f"[UDP] Sending: {cmd_to_send}")  # debug output
    UDP.send_command(cmd_to_send)  # transmit over UDP
    time.sleep(DELAY)  # enforce pacing between commands

'''Calculate and send moves to approach a single waypoint.'''
def move_to_destination(dest):
    """
    Args:
        dest (tuple): Target (x, y) pixel coordinates
    Returns:
        bool: True if destination reached, else False
    """
    time.sleep(DELAY)  # brief pause before computing

    loc = drone_location  # read latest position
    if loc is None:
        print("[UDP] No vision data; skipping move.")  # cannot navigate without a fix
        return False

    # Step 1: compute forward/backward and sideways adjustments
    fwd_cmd, side_cmd = NAV.calculate_from_pixels(loc, dest)  # initial commands
    print(f"[UDP] 1. Calculated cmds: {fwd_cmd}, {side_cmd}")  # report for debugging
    send_command_if_needed(fwd_cmd)  # send forward/backward

    # Step 2: recompute and send lateral adjustment
    loc = drone_location  # get updated position
    _, side_cmd = NAV.calculate_from_pixels(loc, dest)  # adjust sideways only
    print(f"[UDP] 2. Sideways cmd: {side_cmd}")  # log lateral move
    send_command_if_needed(side_cmd)  # send sideways

    # Step 3: verify if within tolerance
    final_loc = drone_location  # final position after moves
    reached = is_close_enough(final_loc, dest, x_tol=128, y_tol=72)  # check arrival
    print(f"[UDP] Final {final_loc}, reached={reached}")  # summary
    return reached

'''Attempt moves up to a maximum retry count.'''
def retry_to_reach(dest, max_retries=3):
    """
    Args:
        dest (tuple): Target (x, y) pixel coordinates
        max_retries (int): Number of attempts before giving up
    """
    for attempt in range(1, max_retries + 1):
        if move_to_destination(dest):
            print(f"[UDP] Destination {dest} reached.")  # success message
            return
        print(f"[UDP] Retry {attempt}/{max_retries} for {dest}")  # log retry
    print(f"[UDP] Failed to reach {dest} after {max_retries} attempts.")  # final failure

'''Drive through all waypoints defined in GUI list.'''
def execute_mission():
    """
    Returns:
        tuple or None: Last waypoint reached, or None if list empty
    """
    last = None  # track last successful destination
    for dest in gui.destination_list:  # iterate waypoints
        retry_to_reach(dest)  # perform movement with retries
        last = dest  # update last attempted
    return last  # return last processed waypoint

def initialize_and_start_stream():
    """
    Open the UDP socket, enter SDK mode, turn on the video stream,
    and launch the camera‐feed thread as soon as 'streamon' returns 'ok'.
    """
    UDP.connect()                # open UDP socket
    time.sleep(DELAY)            # allow socket to settle

    # enter SDK mode
    UDP.send_command('command')
    time.sleep(DELAY)

    # request video stream
    response = UDP.send_command('streamon')
    if response == 'ok':
        # start the feed thread immediately
        threading.Thread(target=drone_feed_run, daemon=True).start()
        print('[UDP] Stream started successfully.')
        time.sleep(DELAY)       # brief settling wait
    else:
        print('[UDP] Stream start failed.')

'''Wait until GUI destination list is populated.'''
def wait_for_mission():
    """
    Blocks until gui.destination_list is non-empty.
    """
    print("[UDP] Awaiting destination list...")  # idle state
    while not gui.destination_list:  # busy-wait until GUI populates list
        time.sleep(DELAY)  # reduce CPU usage

'''Perform drone takeoff sequence.'''
def takeoff_sequence():
    """
    Sends the necessary commands to prepare and take off.
    """
    print("[UDP] Mission start sequence")  # beginning mission
    for cmd in ('command', 'takeoff', 'up 150'):  # prep commands
        UDP.send_command(cmd)  # send each prep command
        time.sleep(DELAY)  # pause after each

'''Wait for initial vision fix.'''
def wait_for_vision_fix():
    """
    Blocks until drone_location is set by vision thread.
    """
    print("[UDP] Waiting for vision fix...")  # prompt
    while drone_location is None:  # spin until vision thread updates
        time.sleep(0.1)  # short wait to avoid tight loop
    print(f"[UDP] First fix: {drone_location}")  # log initial position

'''Report battery level and final drone location.'''
def report_status():
    """
    Queries battery and prints the final position.
    """
    bat = UDP.send_command('battery?')  # query battery
    print(f"[UDP] Battery: {bat}")  # battery status
    print(f"[UDP] Final drone_location: {drone_location}")  # position report

'''Land the drone and cleanup UDP socket and GUI.'''
def land_and_cleanup():
    """
    Sends land command, closes socket, and clears GUI list.
    """
    time.sleep(DELAY)  # wait before landing
    UDP.send_command('land')  # land command
    time.sleep(DELAY)  # wait for land completion
    UDP.close_socket()  # close UDP socket
    gui.destination_list.clear()  # reset for next mission

'''Main UDP logic loop triggering missions.'''
def run():
    print("[UDP] UDP logic thread running...")  # startup notice
    while True:  # continuous operation
        global drone_location  # update global from vision thread
        wait_for_mission()  # block until destinations provided
        initialize_and_start_stream()  # ensure UDP and stream active
        takeoff_sequence()  # lift off
        wait_for_vision_fix()  # get first location fix
        execute_mission()  # fly through all waypoints
        report_status()  # battery and location
        #flip_drone()  # optional flip command
        land_and_cleanup()  # land and reset GUI
