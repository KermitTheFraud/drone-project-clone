# udp_sender.py

import socket

# ─── Tello and local configuration ───────────────────────────────────────────
TELLO_IP   = '192.168.10.1'
TELLO_PORT = 8889
LOCAL_IPS  = ['192.168.10.2', '192.168.10.3']
LOCAL_PORT = 9000
TIMEOUT    = 15.0  # seconds to wait for a reply

_sock = None

def connect():
    """Try each LOCAL_IP in turn until bind() succeeds."""
    global _sock
    _sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    _sock.settimeout(TIMEOUT)

    last_exc = None
    for ip in LOCAL_IPS:
        try:
            _sock.bind((ip, LOCAL_PORT))
            print(f"✔ Bound to {ip}:{LOCAL_PORT}")
            return _sock
        except OSError as e:
            print(f"✘ Could not bind to {ip}:{LOCAL_PORT} → {e}")
            last_exc = e

    # if none worked, re-raise
    raise last_exc

def send_tello(cmd: str) -> str:
    """Send one SDK command and return the response (never blows up on bad bytes)."""
    if _sock is None:
        raise RuntimeError("Socket not connected: call connect() first")
    _sock.sendto(cmd.encode('utf-8'), (TELLO_IP, TELLO_PORT))
    try:
        resp, _ = _sock.recvfrom(1024)
    except socket.timeout:
        return '(timeout)'
    except ConnectionResetError:
        return '(connection reset)'

    # Try UTF-8, fall back silently if there's invalid bytes
    try:
        text = resp.decode('utf-8')
    except UnicodeDecodeError:
        text = resp.decode('utf-8', errors='ignore')
    return text.strip()

def send_command(command: str) -> str:
    """Send + print, retrying up to 5 times on '(timeout)'."""
    for attempt in range(1, 6):
        response = send_tello(command)
        print(f"Response: {response}")
        if response != '(timeout)':
            return response
        print(f"↻ Timeout #{attempt} for '{command}', retrying…")
    return response


def close_socket():
    """Cleanly close the socket."""
    global _sock
    if _sock:
        _sock.close()
        _sock = None