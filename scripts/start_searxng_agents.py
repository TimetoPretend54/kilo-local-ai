import sys
import subprocess
import time
import os
from pathlib import Path

LOCK_FILE = Path.home() / ".kilo_local_ai_searxng.lock"
SEARXNG_COMPOSE_PATH = Path("./docker/searxng/docker-compose.yml")
ENV_FILE = Path("./.env")
FORCE = "--force" in sys.argv or "-f" in sys.argv

def acquire_lock():
    if LOCK_FILE.exists():
        if FORCE:
            print("Force flag detected. Removing existing lock and continuing.")
            LOCK_FILE.unlink()
        else:
            print("Lock file exists. Checking if agents are actually running...")

            # Example check for Ollama
            import socket
            def is_port_open(host, port):
                try:
                    with socket.create_connection((host, port), timeout=1):
                        return True
                except OSError:
                    return False

            ollama_running = is_port_open("127.0.0.1", 11434)
            import subprocess
            searxng_running = False
            try:
                result = subprocess.run(
                    ["docker-compose", "-f", str(SEARXNG_COMPOSE_PATH), "ps", "--filter", "name=searxng", "--format", "{{.Names}}"],
                    capture_output=True, text=True
                )
                searxng_running = bool(result.stdout.strip())
            except Exception:
                pass

            if not (ollama_running or searxng_running):
                print("No agents detected. Removing stale lock file.")
                LOCK_FILE.unlink()
            else:
                print("Agents already running. Use --force flag to remove lock. Exiting.")
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
