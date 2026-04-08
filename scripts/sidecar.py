import time
import logging
import subprocess
import os
import sys

# Try to import python-dotenv if available to load local credentials
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from supabase import create_client

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(message)s', datefmt='%H:%M:%S')
log = logging.getLogger("AishaSidecar")

class LocalSidecar:
    """
    JARVIS Phase 2 Upgrade: The Local Python Sidecar.
    Runs on the user's local machine, polling the Supabase broker for commands.
    """
    def __init__(self):
        self.machine_id = os.uname().nodename if hasattr(os, 'uname') else "local-laptop"
        url = os.environ.get("SUPABASE_URL", "")
        key = os.environ.get("SUPABASE_SERVICE_KEY")

        if not url or not key:
            log.error("Missing SUPABASE_SERVICE_KEY in environment. Sidecar requires service-level access to prevent RCE. Cannot start.")
            sys.exit(1)

        self.supabase = create_client(url, key)
        log.info(f"Starting Aisha Sidecar on {self.machine_id}...")
        log.info("Successfully connected to the Cloud Brain broker.")

    def run_command(self, command: str) -> str:
        log.info(f"Executing local command: {command}")
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=10
            )
            output = result.stdout if result.returncode == 0 else result.stderr
            return output.strip()
        except Exception as e:
            return f"Error executing command: {e}"

    def poll_loop(self):
        log.info("Listening for commands... (Press Ctrl+C to stop)")
        try:
            while True:
                # Poll for pending commands
                res = self.supabase.table("sidecar_commands").select("*").eq("sidecar_id", self.machine_id).eq("status", "pending").execute()

                for cmd in res.data:
                    task_id = cmd["id"]
                    log.info(f"Received task {task_id}: {cmd['command_type']}")

                    # Mark as processing
                    self.supabase.table("sidecar_commands").update({"status": "processing"}).eq("id", task_id).execute()

                    # Execute
                    if cmd['command_type'] == 'shell_exec':
                        output = self.run_command(cmd['payload'].get('command', ''))

                        # Return result
                        self.supabase.table("sidecar_commands").update({
                            "status": "completed",
                            "result": {"output": output}
                        }).eq("id", task_id).execute()

                time.sleep(2)
        except KeyboardInterrupt:
            log.info("Shutting down sidecar...")
        except Exception as e:
            log.error(f"Sidecar error: {e}")

if __name__ == "__main__":
    sidecar = LocalSidecar()
    sidecar.poll_loop()
