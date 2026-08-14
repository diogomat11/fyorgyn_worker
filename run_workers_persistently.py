import subprocess
import os
import time

ports = [9000, 9001, 9002, 9003, 9004, 9005, 9006]
processes = []

# Start each worker server
for port in ports:
    env = os.environ.copy()
    env["PORT"] = str(port)
    env["SGUCARD_HEADLESS"] = "true"
    print(f"Starting worker server on port {port}...")
    p = subprocess.Popen(
        ["python", "Worker/server.py"],
        cwd="c:/dev/Agenda_hub_MultiConv/Local_worker",
        env=env
    )
    processes.append(p)

# Wait a second for servers to boot
time.sleep(3)

# Start dispatcher
env_dispatcher = os.environ.copy()
server_urls_list = []
for p in ports:
    if p in (9005, 9006):
        server_urls_list.append(f"http://127.0.0.1:{p}:agendamento")
    else:
        server_urls_list.append(f"http://127.0.0.1:{p}")
env_dispatcher["API_SERVER_URLS"] = ",".join(server_urls_list)

print("Starting dispatcher...")
p_disp = subprocess.Popen(
    ["python", "Worker/dispatcher.py"],
    cwd="c:/dev/Agenda_hub_MultiConv/Local_worker",
    env=env_dispatcher
)
processes.append(p_disp)

print("All background workers started! Keeping script alive to prevent Job Object cleanup...")

# Infinite sleep loop
try:
    while True:
        time.sleep(60)
except KeyboardInterrupt:
    print("Exiting...")
    for p in processes:
        p.terminate()
