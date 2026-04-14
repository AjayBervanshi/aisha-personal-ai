"""
code_sandbox.py
===============
Aisha's Code Execution Sandbox.
Provides an isolated, secure environment for executing Python scripts using the E2B API.
This allows Aisha to safely verify her tech channel coding scripts, read tracebacks, and self-correct.
"""

import os
import logging

log = logging.getLogger("Aisha.CodeSandbox")

def execute_python_code(code_string: str) -> dict:
    """
    Executes a Python script in a secure E2B cloud container.
    Requires E2B_API_KEY to be set in Supabase or environment.

    Returns:
        {
            "success": bool,
            "output": str (stdout + stderr),
            "error": str | None
        }
    """
    from src.core.config import _get
    e2b_key = _get("E2B_API_KEY", required=True)
    if not e2b_key or "your_" in e2b_key:
        return {"success": False, "output": "", "error": "Missing E2B_API_KEY for code execution sandbox."}

    log.info("[CodeSandbox] Spinning up secure E2B cloud environment...")

    try:
        from e2b import Sandbox

        # Initialize a default Python environment Sandbox
        # https://e2b.dev/docs/guide/custom-sandbox
        with Sandbox(api_key=e2b_key, template="base") as sandbox:
            # We can run bash commands directly or write the script to a file and execute

            # Step 1: Write the python script into the secure container
            sandbox.filesystem.write("/home/user/script.py", code_string)

            # Step 2: Execute the python script and capture the output
            # process = sandbox.process.start("python3 /home/user/script.py")
            process = sandbox.process.start_and_wait("python3 /home/user/script.py", timeout=30)

            stdout = process.stdout
            stderr = process.stderr
            exit_code = process.exit_code

            output = (stdout + "\n" + stderr).strip()

            if exit_code == 0:
                log.info(f"[CodeSandbox] Execution successful. Extracted {len(stdout)} chars of output.")
                return {"success": True, "output": output, "error": None}
            else:
                log.warning(f"[CodeSandbox] Execution failed with exit code {exit_code}: {stderr[:100]}...")
                return {"success": False, "output": output, "error": f"Process exited with code {exit_code}"}

    except ImportError:
        err_msg = "Please run `pip install e2b` to use the code execution sandbox."
        log.error(err_msg)
        return {"success": False, "output": "", "error": err_msg}
    except Exception as e:
        err_msg = f"E2B Sandbox API failed: {e}"
        log.error(err_msg)
        return {"success": False, "output": "", "error": err_msg}
