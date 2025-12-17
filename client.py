# client.py by Pahlavanian
import socket
import argparse
import json
from datetime import datetime
import base64
from pathlib import Path
import time

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 5000

def encode_image(path: Path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("ascii")

def send_event(host, port, event, camera, image_path=None):
    payload = {  #imp
        "event": event,
        "camera": camera,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }
    if image_path:
        p = Path(image_path)
        if p.exists():
            payload["image_filename"] = p.name
            payload["image_b64"] = encode_image(p)
        else:
            print("Warning: image file not found:", image_path)
    raw = json.dumps(payload) + "\n"
    with socket.create_connection((host, port), timeout=10) as s: #imp
        s.sendall(raw.encode("utf-8"))
    print("Sent event:", event)

def main():
    parser = argparse.ArgumentParser(description="DVR event client")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", default=DEFAULT_PORT, type=int)
    parser.add_argument("--event", default="MOTION_DETECTED")
    parser.add_argument("--camera", default="cam1")
    parser.add_argument("--image", default=None, help="optional image file to include")
    parser.add_argument("--loop", type=float, default=0.0, help="send events repeatedly every N seconds (0 = one shot)")
    args = parser.parse_args()

    if args.loop and args.loop > 0:
        print(f"Sending events every {args.loop} seconds. Ctrl+C to stop.")
        try:
            while True:
                send_event(args.host, args.port, args.event, args.camera, args.image)
                time.sleep(args.loop)
        except KeyboardInterrupt:
            print("Stopped.")
    else:
        send_event(args.host, args.port, args.event, args.camera, args.image)

if __name__ == "__main__":
    main()
