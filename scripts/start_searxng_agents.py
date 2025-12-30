import subprocess
import time
import os
from pathlib import Path

LOCK_FILE = Path.home() / ".kilo_local_ai_searxng.lock"
SEARXNG_COMPOSE_PATH = Path("./docker/searxng/docker-compose.yml")
ENV_FILE = Path("./.env")

def acquire_lock():
    if LOCK_FILE.exists():
        print("SearxNG already running (lock file exists).")
        exit(0)
    LOCK_FILE.write_text(str(os.getpid()))

def release_lock():
    if LOCK_FILE.exists():
        LOCK_FILE.unlink()

def start_searxng():
    print("Starting SearxNG...")
    result = subprocess.run(
        [
            "docker-compose",
            "-f", str(SEARXNG_COMPOSE_PATH),
            "--env-file", str(ENV_FILE),
            "up", "-d"
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        print("SearxNG container started.")
    else:
        print("Warning: SearxNG may not have started correctly.")
        print(result.stderr)

def stop_searxng():
    subprocess.run(
        [
            "docker-compose",
            "-f", str(SEARXNG_COMPOSE_PATH),
            "--env-file", str(ENV_FILE),
            "down"
        ]
    )
    print("SearxNG container stopped.")

def main():
    acquire_lock()
    start_searxng()
    print("SearxNG running. Press Ctrl+C to stop and release lock.")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping SearxNG...")
        stop_searxng()
        release_lock()
        print("Lock released.")

if __name__ == "__main__":
    main()
