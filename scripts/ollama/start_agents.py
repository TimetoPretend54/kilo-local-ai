import sys
import subprocess
import time
import os
import platform
import socket
from pathlib import Path
import shutil

LOCK_FILE = Path.home() / ".kilo_local_ai.lock"
OLLAMA_HOST = ("127.0.0.1", 11434)
SEARXNG_COMPOSE_PATH = Path("./docker/searxng/docker-compose.yml")
ENV_FILE = Path("./.env")
FORCE = "--force" in sys.argv or "-f" in sys.argv

# -----------------------
# Helper functions
# -----------------------

def is_port_open(host, port):
    try:
        with socket.create_connection((host, port), timeout=1):
            return True
    except OSError:
        return False

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

def detect_docker_cli():
    if shutil.which("docker-compose"):
        return "docker-compose"
    elif shutil.which("docker"):
        return "docker"
    else:
        print("Error: Docker CLI not found.")
        exit(1)

def start_ollama():
    if is_port_open(*OLLAMA_HOST):
        print("Ollama already running (Desktop/service).")
        return

    print("Starting Ollama...")
    subprocess.Popen(
        ["ollama", "serve"],
        shell=(platform.system() == "Windows"),
    )

    for _ in range(12):
        if is_port_open(*OLLAMA_HOST):
            print("Ollama listening on 127.0.0.1:11434")
            return
        time.sleep(0.5)

    print("Warning: Ollama did not become ready in time.")

def start_searxng():
    print("Starting SearxNG...")
    docker_cli = detect_docker_cli()
    cmd = [docker_cli, "compose", "-f", str(SEARXNG_COMPOSE_PATH),
           "--env-file", str(ENV_FILE), "up", "-d"] if docker_cli == "docker" else \
          [docker_cli, "-f", str(SEARXNG_COMPOSE_PATH),
           "--env-file", str(ENV_FILE), "up", "-d"]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        print("SearxNG container started.")
    else:
        print("Warning: SearxNG may not have started correctly.")
        print(result.stderr)

def stop_searxng():
    docker_cli = detect_docker_cli()
    cmd = [docker_cli, "compose", "-f", str(SEARXNG_COMPOSE_PATH),
           "--env-file", str(ENV_FILE), "down"] if docker_cli == "docker" else \
          [docker_cli, "-f", str(SEARXNG_COMPOSE_PATH),
           "--env-file", str(ENV_FILE), "down"]
    subprocess.run(cmd)

def print_health_summary():
    print("\n===== Agent Health Summary =====")
    print(f"Ollama: {'Running' if is_port_open(*OLLAMA_HOST) else 'Stopped'}")

    docker_cli = shutil.which("docker") or shutil.which("docker-compose")
    if docker_cli is None:
        print("SearxNG: Unknown (Docker not found)")
    else:
        cmd = [docker_cli, "ps", "--filter", "name=searxng", "--format", "{{.Names}}"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        names = [n.strip() for n in result.stdout.strip().splitlines() if n.strip()]
        searx_status = "Running" if names else "Stopped"
        print(f"SearxNG: {searx_status}")

    print("================================\n")

def stop_agents():
    print("\nStopping agents...")
    stop_searxng()
    release_lock()
    print("Agents stopped.")

    # Final health summary
    print("\n===== Final Agent Status =====")
    print(f"Ollama: {'Running' if is_port_open(*OLLAMA_HOST) else 'Stopped'}")

    docker_cli = shutil.which("docker") or shutil.which("docker-compose")
    if docker_cli is None:
        print("SearxNG: Unknown (Docker not found)")
    else:
        cmd = [docker_cli, "ps", "--filter", "name=searxng", "--format", "{{.Names}}"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        names = [n.strip() for n in result.stdout.strip().splitlines() if n.strip()]
        searx_status = "Running" if names else "Stopped"
        print(f"SearxNG: {searx_status}")

    print("================================\n")

# -----------------------
# Main loop
# -----------------------

def main():
    acquire_lock()
    start_ollama()
    start_searxng()
    print_health_summary()

    print("Agents running. Press Ctrl+C to exit.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        stop_agents()

if __name__ == "__main__":
    main()
