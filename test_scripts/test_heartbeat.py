import requests
import socket

def test_heartbeat():
    api_url = "http://127.0.0.1:8000"
    hostname = socket.gethostname() + "-TEST"
    payload = {
        "hostname": hostname,
        "status": "idle",
        "current_job_id": None,
        "meta": {"type": "test"}
    }
    
    try:
        print(f"Sending heartbeat to {api_url}/workers/heartbeat...")
        resp = requests.post(f"{api_url}/workers/heartbeat", json=payload, timeout=5)
        print(f"Response ({resp.status_code}): {resp.json()}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_heartbeat()
