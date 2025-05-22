import time  # time delays
import subprocess  # shell commands
import platform  # OS detection
import atexit  # exit handler

TELLO_SSID = "TELLO-E9C59F"  # drone network SSID
CHECK_INTERVAL = 2  # seconds between connection attempts

_saved_ssid = None

def get_current_wifi():
    """
    Returns:
        str or None: current SSID if on Windows, else None
    """
    if platform.system() != "Windows":
        return None  # unsupported on non-Windows
    try:
        output = subprocess.check_output(
            ["netsh", "wlan", "show", "interfaces"], text=True
        )  # query WLAN status
        for line in output.splitlines():
            if "SSID" in line and "BSSID" not in line:
                return line.split(":", 1)[1].strip()  # extract SSID
    except Exception:
        pass
    return None

def disconnect_wifi():
    """
    Disconnects current Wi-Fi on Windows.
    """
    if platform.system() != "Windows":
        return
    try:
        subprocess.run(["netsh", "wlan", "disconnect"], check=True)
    except Exception:
        pass  # ignore failures

def attempt_connect(ssid):
    """
    Args:
        ssid (str): SSID to connect
    Returns:
        bool: True if now connected, else False
    """
    if platform.system() != "Windows":
        return False
    try:
        subprocess.run(
            ["netsh", "wlan", "connect", f"name={ssid}"],
            stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL, check=True
        )  # connect by profile name
    except Exception:
        return False
    return get_current_wifi() == ssid  # verify

def save_current_ssid():
    """
    Stores current network SSID in module global.
    """
    global _saved_ssid
    _saved_ssid = get_current_wifi()  # capture original
    print(f"[WIFI] Saved SSID: {_saved_ssid}")

def restore_saved_ssid():
    """
    Reconnects to the SSID saved earlier.
    """
    if not _saved_ssid:
        print("[WIFI] No SSID to restore.")
        return
    attempt_connect(_saved_ssid)  # reconnect
    print(f"[WIFI] Restored SSID: {_saved_ssid}")

atexit.register(restore_saved_ssid)  # ensure restore on exit

def connect_to_tello():
    """
    Loops until drone SSID is active.
    """
    print(f"[WIFI] Trying to join {TELLO_SSID}...")
    while True:
        current = get_current_wifi()  # check active SSID
        if current == TELLO_SSID:
            print(f"[WIFI] Connected to {TELLO_SSID}")
            break
        disconnect_wifi()  # drop existing
        attempt_connect(TELLO_SSID)  # try join
        time.sleep(CHECK_INTERVAL)  # wait before retry

def run():
    """
    Saves original SSID, then connects to drone.
    """
    if platform.system() != "Windows":
        print("[WIFI] Unsupported OS. Exiting.")
        return
    save_current_ssid()  # preserve before change
    connect_to_tello()  # join drone network

if __name__ == "__main__":
    run()  # start process
