import os
import subprocess
import logging
import platform

log = logging.getLogger("AishaDesktop")

class DesktopController:
    """
    Cross-platform desktop automation for Aisha's Sidecar (Feature 2.2).
    Uses native OS commands (PowerShell on Windows, xdotool/wmctrl on Linux, AppleScript on Mac)
    to interact with the desktop without heavy third-party dependencies.
    """
    def __init__(self):
        self.os_type = platform.system().lower()
        log.info(f"Desktop Controller initialized for {self.os_type}")

    def list_windows(self) -> str:
        """Returns a list of currently open visible windows."""
        try:
            if self.os_type == 'windows':
                cmd = ['powershell', '-Command', 'Get-Process | Where-Object {$_.MainWindowTitle} | Select-Object MainWindowTitle | Format-List']
                return subprocess.check_output(cmd, shell=False, text=True).strip()

            elif self.os_type == 'linux':
                # Requires wmctrl installed on Linux
                return subprocess.check_output(["wmctrl", "-l"], text=True).strip()

            elif self.os_type == 'darwin':
                cmd = ["osascript", "-e", 'tell application "System Events" to get name of every window of (every process whose background only is false)']
                return subprocess.check_output(cmd, text=True).strip()

            return f"Window listing not supported on {self.os_type}"
        except Exception as e:
            return f"Failed to list windows: {e}"

    def focus_window(self, window_title: str) -> str:
        """Brings a specific window to the foreground."""
        try:
            if self.os_type == 'windows':
                # Escape single quotes for PowerShell string
                safe_title = window_title.replace("'", "''")
                script = f"""
                $wshell = New-Object -ComObject wscript.shell;
                $wshell.AppActivate('{safe_title}')
                """
                subprocess.run(["powershell", "-Command", script], capture_output=True)
                return f"Focused {window_title}"

            elif self.os_type == 'linux':
                subprocess.run(["wmctrl", "-a", window_title], capture_output=True)
                return f"Focused {window_title}"

            elif self.os_type == 'darwin':
                # Escape double quotes for AppleScript string
                safe_title = window_title.replace('"', '\\"')
                script = f'tell application "{safe_title}" to activate'
                subprocess.run(["osascript", "-e", script], capture_output=True)
                return f"Focused {window_title}"

            return f"Focusing not supported on {self.os_type}"
        except Exception as e:
            return f"Failed to focus window: {e}"

    def type_text(self, text: str) -> str:
        """Simulates typing text on the keyboard."""
        try:
            if self.os_type == 'windows':
                # Escape single quotes and curly braces for SendKeys
                safe_text = text.replace("'", "''").replace("{", "{{}").replace("}", "{}}")
                script = f"""
                $wshell = New-Object -ComObject wscript.shell;
                $wshell.SendKeys('{safe_text}')
                """
                subprocess.run(["powershell", "-Command", script], capture_output=True)
                return "Typed text"

            elif self.os_type == 'linux':
                # Requires xdotool
                subprocess.run(["xdotool", "type", text], capture_output=True)
                return "Typed text"

            elif self.os_type == 'darwin':
                # Escape double quotes and backslashes for AppleScript string
                safe_text = text.replace('\\', '\\\\').replace('"', '\\"')
                script = f'tell application "System Events" to keystroke "{safe_text}"'
                subprocess.run(["osascript", "-e", script], capture_output=True)
                return "Typed text"

            return f"Typing not supported on {self.os_type}"
        except Exception as e:
            return f"Failed to type text: {e}"

desktop_controller = DesktopController()
